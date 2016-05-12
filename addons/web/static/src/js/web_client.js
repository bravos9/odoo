odoo.define('web.WebClient', function (require) {
"use strict";

var AbstractWebClient = require('web.AbstractWebClient');
var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
var framework = require('web.framework');
var Menu = require('web.Menu');
var Model = require('web.DataModel');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var UserMenu = require('web.UserMenu');

return AbstractWebClient.extend({
    events: {
        'click .oe_logo_edit_admin': 'logo_edit',
        'click .oe_logo img': function(ev) {
            ev.preventDefault();
            return this.clear_uncommitted_changes().then(function() {
                framework.redirect("/web" + (core.debug ? "?debug" : ""));
            });
        },
    },
    show_application: function() {
        var self = this;
        self.toggle_bars(true);

        self.update_logo();

        // Menu is rendered server-side thus we don't want the widget to create any dom
        self.menu = new Menu(self);
        self.menu.setElement(this.$el.parents().find('.oe_application_menu_placeholder'));
        self.menu.on('menu_click', this, this.on_menu_action);

        // Create the user menu (rendered client-side)
        self.user_menu = new UserMenu(self);
        var $user_menu_placeholder = $('body').find('.oe_user_menu_placeholder').show();
        var user_menu_loaded = self.user_menu.appendTo($user_menu_placeholder);

        // Create the systray menu (rendered server-side)
        self.systray_menu = new SystrayMenu(self);
        self.systray_menu.setElement(this.$el.parents().find('.oe_systray'));
        var systray_menu_loaded = self.systray_menu.start();

        // Start the menu once both systray and user menus are rendered
        // to prevent overflows while loading
        $.when(systray_menu_loaded, user_menu_loaded).done(function() {
            self.menu.start();
        });

        self.bind_hashchange();
        self.set_title();
        if (self.client_options.action_post_login) {
            self.action_manager.do_action(self.client_options.action_post_login);
            delete(self.client_options.action_post_login);
        }
    },
    toggle_bars: function(value) {
        this.$('tr:has(td.navbar),.oe_leftbar').toggle(value);
    },
    update_logo: function() {
        var company = session.company_id;
        var img = session.url('/web/binary/company_logo' + '?db=' + session.db + (company ? '&company=' + company : ''));
        this.$('.oe_logo img').attr('src', '').attr('src', img);
        this.$('.oe_logo_edit').toggleClass('oe_logo_edit_admin', session.uid === 1);
    },
    logo_edit: function(ev) {
        var self = this;
        ev.preventDefault();
        self.alive(new Model("res.users").get_func("read")(session.uid, ["company_id"])).then(function(res) {
            self.rpc("/web/action/load", { action_id: "base.action_res_company_form" }).done(function(result) {
                result.res_id = res.company_id[0];
                result.target = "new";
                result.views = [[false, 'form']];
                result.flags = {
                    action_buttons: true,
                    headless: true,
                };
                self.action_manager.do_action(result);
                var form = self.action_manager.dialog_widget.views.form.controller;
                form.on("on_button_discard", self.action_manager, self.action_manager.dialog_stop);
                form.on('record_saved', self, function() {
                    self.action_manager.dialog_stop();
                    self.update_logo();
                });
            });
        });
        return false;
    },
    bind_hashchange: function() {
        var self = this;
        $(window).bind('hashchange', this.on_hashchange);

        var state = $.bbq.getState(true);
        if (_.isEmpty(state) || state.action === "login") {
            self.menu.is_bound.done(function() {
                new Model("res.users").call("read", [session.uid, ["action_id"]]).done(function(data) {
                    if(data.action_id) {
                        self.action_manager.do_action(data.action_id[0]);
                        self.menu.open_action(data.action_id[0]);
                    } else {
                        var first_menu_id = self.menu.$el.find("a:first").data("menu");
                        if(first_menu_id) {
                            self.menu.menu_click(first_menu_id);
                        }
                    }
                });
            });
        } else {
            $(window).trigger('hashchange');
        }
    },
    on_hashchange: function(event) {
        var self = this;
        var stringstate = event.getState(false);
        if (!_.isEqual(this._current_state, stringstate)) {
            var state = event.getState(true);
            if(!state.action && state.menu_id) {
                self.menu.is_bound.done(function() {
                    self.menu.menu_click(state.menu_id);
                });
            } else {
                state._push_me = false;  // no need to push state back...
                this.action_manager.do_load_state(state, !!this._current_state).then(function () {
                    var action = self.action_manager.get_inner_action();
                    if (action) {
                        self.menu.open_action(action.action_descr.id);
                    }
                });
            }
        }
        this._current_state = stringstate;
    },
    on_menu_action: function(options) {
        var self = this;
        return this.menu_dm.add(data_manager.load_action(options.action_id))
            .then(function (result) {
                return self.action_mutex.exec(function() {
                    if (options.needaction) {
                        result.context = new data.CompoundContext(result.context, {
                            search_default_message_needaction: true,
                            search_disable_custom_filters: true,
                        });
                    }
                    var completed = $.Deferred();
                    $.when(self.action_manager.do_action(result, {
                        clear_breadcrumbs: true,
                        action_menu_id: self.menu.current_menu,
                    })).fail(function() {
                        self.menu.open_menu(options.previous_menu_id);
                    }).always(function() {
                        completed.resolve();
                    });
                    setTimeout(function() {
                        completed.resolve();
                    }, 2000);
                    // We block the menu when clicking on an element until the action has correctly finished
                    // loading. If something crash, there is a 2 seconds timeout before it's unblocked.
                    return completed;
                });
            });
    },
    toggle_fullscreen: function(fullscreen) {
        this._super(fullscreen);
        if (!fullscreen) {
            this.menu.reflow();
        }
    },
});

});
