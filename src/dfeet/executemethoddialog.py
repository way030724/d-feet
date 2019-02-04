# -*- coding: utf-8 -*-
import time
from pprint import pformat
from gi.repository import GLib, Gio, Gtk


@Gtk.Template(resource_path='/org/gnome/dfeet/executedialog.ui')
class ExecuteMethodDialog(Gtk.Dialog):

    __gtype_name__ = 'ExecuteMethodDialog'

    label_method_name = Gtk.Template.Child()
    label_bus_name = Gtk.Template.Child()
    label_interface = Gtk.Template.Child()
    label_object_path = Gtk.Template.Child()

    source_textview = Gtk.Template.Child()
    parameter_textview = Gtk.Template.Child()
    prettyprint_textview = Gtk.Template.Child()

    method_exec_count_spinbutton = Gtk.Template.Child()

    label_avg = Gtk.Template.Child()
    label_min = Gtk.Template.Child()
    label_max = Gtk.Template.Child()


    def __init__(self, connection, connection_is_bus, bus_name,
                 method_obj, parent_window):
        super(ExecuteMethodDialog, self).__init__()

        self.set_transient_for(parent_window)

        self.connection = connection
        self.connection_is_bus = connection_is_bus
        self.bus_name = bus_name
        self.method_obj = method_obj

        self.label_method_name.set_markup("%s" % (self.method_obj.markup_str))
        self.label_bus_name.set_text(self.bus_name)
        self.label_object_path.set_markup("%s" % (self.method_obj.object_path))
        self.label_interface.set_markup("%s" % (self.method_obj.iface_info.name))

    @Gtk.Template.Callback('execute_dbus_method_cb')
    def execute_cb(self, widget):
        # get given parameters
        buf = self.parameter_textview.get_buffer()
        params = buf.get_text(buf.get_start_iter(),
                              buf.get_end_iter(), False)

        # reset the statistics stuff
        self.label_avg.set_text("")
        self.label_min.set_text("")
        self.label_max.set_text("")
        user_data = {
            'avg': 0,
            'count': 0,
            }

        try:
            # build a GVariant
            if params:
                params = "(" + params + ",)"
                params_code = '(' + self.method_obj.in_args_code + ')'
                params_gvariant = GLib.Variant(params_code, eval(params))
            else:
                params_gvariant = None

            if self.connection_is_bus:
                proxy = Gio.DBusProxy.new_sync(self.connection,
                                               Gio.DBusProxyFlags.NONE,
                                               None,
                                               self.bus_name,
                                               self.method_obj.object_path,
                                               self.method_obj.iface_info.name,
                                               None)
                # call the function
                method_exec_count = self.method_exec_count_spinbutton.get_value_as_int()
                for i in range(0, method_exec_count):
                    user_data['method_call_time_start'] = time.time()
                    proxy.call(
                        self.method_obj.method_info.name, params_gvariant,
                        Gio.DBusCallFlags.NONE, -1, None, self.method_connection_bus_cb, user_data)
            else:
                # FIXME: implement p2p connection execution
                raise Exception("Function execution on p2p connections not yet implemented")
                # self.connection.call(
                # None, object_path, self.method_obj.iface_obj.iface_info.name,
                # self.method_obj.method_info.name, params_gvariant,
                # GLib.VariantType.new("(s)"), Gio.DBusCallFlags.NONE, -1, None)

        except Exception as e:
            # output the exception
            self.source_textview.get_buffer().set_text(str(e))
            self.prettyprint_textview.get_buffer().set_text(pformat(str(e)))

    def method_connection_bus_cb(self, proxy, res_async, user_data):
        """async callback for executed method"""
        try:
            # get the result from the dbus method call
            result = proxy.call_finish(res_async)
            # remember the needed time for the method call
            method_call_time_end = time.time()
            method_call_time_needed = method_call_time_end - user_data['method_call_time_start']

            # update avg, min, max
            user_data['avg'] += method_call_time_needed
            user_data['count'] += 1
            self.label_avg.set_text("%.4f" % (float(user_data['avg'] / user_data['count'])))
            self.label_min.set_text(
                "%.4f" % min(float(self.label_min.get_text() or "999"), method_call_time_needed))
            self.label_max.set_text(
                "%.4f" % max(float(self.label_max.get_text() or "0"), method_call_time_needed))

            # output result
            if result:
                self.source_textview.get_buffer().set_text(str(result))
                lines = [pformat(x) for x in result.unpack()]
                self.prettyprint_textview.get_buffer().set_text(',\n'.join(lines))
            else:
                self.prettyprint_textview.get_buffer().set_text(
                    'This method did not return anything')
        except Exception as e:
            # output the exception
            self.source_textview.get_buffer().set_text(str(e))
            self.prettyprint_textview.get_buffer().set_text(pformat(str(e)))

    def run(self):
        response = self.run()
        if response == Gtk.ResponseType.DELETE_EVENT or response == Gtk.ResponseType.CLOSE:
            self.destroy()

    @Gtk.Template.Callback('execute_dialog_close_cb')
    def close_cb(self, widget):
        self.destroy()
