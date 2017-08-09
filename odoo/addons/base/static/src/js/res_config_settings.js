odoo.define('base.settings', function (require) {
"use strict";

var core = require('web.core');
var field_utils = require('web.field_utils');
var FormView = require('web.FormView');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var BasicModel = require('web.BasicModel');
var ControlPanelMixin = require('web.ControlPanelMixin');
var session = require('web.session');
var view_registry = require('web.view_registry');

var QWeb = core.qweb;
var _t = core._t;
var _lt = core._lt;

var BaseSettingRenderer = FormRenderer.extend({
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .appContainer': '_onAppContainerClicked',
        'keyup .searchInput': '_onKeyUpSearch',
    }),

    start: function() {
        this._super.apply(this, arguments);

        var self = this;
        this.navBarDatas = {};
        this.$('.setting_view').each(function() {
            var string = $(this).attr('data-string');
            var key = $(this).attr('data-key');
            var group = !$(this).hasClass('o_invisible_modifier');
            $(this).toggleClass('setting_view ' + key+'_setting_view')
            self.navBarDatas[key] = {
                key: key,
                string: string,
                group: group,
                currentModule: self.currentModule === key,
                imgurl: key==="generalsettings" ? "/base/static/description/settings.png" : "/"+key+"/static/description/icon.png"
            };
        });
        this.$('.apps').append(QWeb.render('basesetting.appContainer',{navBarDatas : _.values(this.navBarDatas)}));


        $.expr[':'].contains = function(a, i, m) {
            return jQuery(a).text().toUpperCase()
                .indexOf(m[3].toUpperCase()) >= 0;
        };

        this.searchText = "";
        this.selectedApp = this.$('.selected');
        this.selectedSetting = this.$('.show');
        this.seatchInput = this.$('.searchInput');
        this.appContainer = this.$('.appContainer');
        this.modules = {};
        var self = this;
        this.appContainer.each(function(app) {
            var settingName = $(this).attr('setting');
            var settingDiv = self.$('.' + settingName + '_setting_view');
            var appName = $(this).find('.app_name').html();
            self.modules[settingName] = {
                appContainer: $(this),
                settingDiv: settingDiv,
                appName: appName
            }
            settingDiv.prepend($("<div>").html('<div class="logos '+settingName+'"></div><span class="appName">'+appName+'</span>').addClass('settingSearchHeader o_hidden'));
        });
    },

    _onAppContainerClicked: function(event) {
        if(this.searchText.length > 0) {
            this.seatchInput.val('');
            this.searchText = "";
            this._searchSetting();
        }
        var settingName = this.$(event.currentTarget).attr('setting');
        this.selectedApp.removeClass('selected');
        this.selectedApp = this.$(event.currentTarget).addClass('selected');;
        this.selectedSetting.addClass('o_hidden').removeClass('show');
        this.selectedSetting = this.$('.' + settingName + '_setting_view');
        this.selectedSetting.removeClass('o_hidden').addClass('show');
    },

    _onKeyUpSearch: function(event) {
        this.searchText = this.seatchInput.val();
        this.selectedApp.removeClass('selected');
        this._searchSetting();
    },

    _searchSetting: function() {
        var self = this;
        this.count = 0;
        _.each(this.modules,function(module) {
            module.settingDiv.find('.o_setting_box').addClass('o_hidden');
            module.settingDiv.find('h2').addClass('o_hidden');
            module.settingDiv.find('.settingSearchHeader').addClass('o_hidden');
            module.settingDiv.find('.o_settings_container').removeClass('mt16');
            var resultSetting = module.settingDiv.find("label:contains('" + self.searchText + "')");
            if (resultSetting.length > 0) {
                resultSetting.each(function() {
                    $(this).closest('.o_setting_box').removeClass('o_hidden');
                    $(this).html(self._wordHiliter($(this).html(),self.searchText));
                });
                module.settingDiv.find('.settingSearchHeader').removeClass('o_hidden');
                module.settingDiv.removeClass('o_hidden');
            } else {
                ++self.count;
            }
        });
        if(this.count == _.size(this.modules)) {
            this.$('.notFound').removeClass('o_hidden');
        } else {
            this.$('.notFound').addClass('o_hidden');
        }
        if(this.searchText.length == 0) {
            this._resetSearch();
        }
    },

    _wordHiliter: function(text,word) {
        if (text.indexOf('hiliterWord') !== -1) {
            text = text.replace('<span class="hiliterWord">', "");
            text = text.replace("</span>", "");
        }
        var match = text.search(new RegExp(word, "i"));
        word = text.substring(match, match+word.length);
        var hilitedWord = "<span class='hiliterWord'>" + word + '</span>';
        return text.replace(word,hilitedWord);
    },

    _resetSearch: function() {
        this.seatchInput.val("");
        _.each(this.modules,function(module) {
            module.settingDiv.addClass('o_hidden');
            module.settingDiv.find('.o_setting_box').removeClass('o_hidden');
            module.settingDiv.find('h2').removeClass('o_hidden');
            module.settingDiv.find('.settingSearchHeader').addClass('o_hidden');
            module.settingDiv.find('.o_settings_container').addClass('mt16');
        });
        this.selectedApp.removeClass('o_hidden').addClass('selected');
        this.selectedSetting.removeClass('o_hidden');
    }

});

var BaseSettingController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.renderer.currentModule = this.initialState.context.module;
    },
});

var BaseSettingView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Renderer: BaseSettingRenderer,
        Controller: BaseSettingController,
    }),
});

view_registry.add('base_settings', BaseSettingView);

return {
    Renderer: BaseSettingRenderer,
    Controller: BaseSettingController,
};
});
