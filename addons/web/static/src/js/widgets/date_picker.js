odoo.define('web.datepicker', function (require) {
"use strict";

var core = require('web.core');
var field_utils = require('web.field_utils');
var time = require('web.time');
var Widget = require('web.Widget');

var _t = core._t;

var DateWidget = Widget.extend({
    template: "web.datepicker",
    type_of_date: "date",
    events: {
        'dp.change': 'changeDatetime',
        'dp.show': 'setDatetimeDefault',
        'change .o_datepicker_input': 'changeDatetime',
    },
    init: function(parent, options) {
        this._super.apply(this, arguments);

        var l10n = _t.database.parameters;

        this.name = parent.name;
        this.options = _.defaults(options || {}, {
            format : time.strftime_to_moment_format((this.type_of_date === 'datetime')? (l10n.date_format + ' ' + l10n.time_format) : l10n.date_format),
            minDate: moment({ y: 1900 }),
            maxDate: moment().add(200, "y"),
            calendarWeeks: true,
            icons: {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                next: 'fa fa-chevron-right',
                previous: 'fa fa-chevron-left',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down',
                close: 'fa fa-times',
            },
            locale : moment.locale(),
            allowInputToggle: true,
            keyBinds: null,
        });
    },
    start: function() {
        this.$input = this.$('input.o_datepicker_input');
        this.$input.focus(function(e) {
            e.stopImmediatePropagation();
        });
        this.$input.datetimepicker(this.options);
        this.picker = this.$input.data('DateTimePicker');
        this.$input.click(this.picker.toggle.bind(this.picker));
        this.setReadonly(false);
    },
    setValue: function(value) {
        this.set({'value': value});
        var formatted_value = value ? this.formatClient(value) : null;
        this.$input.val(formatted_value);
        if (this.picker) {
            this.picker.date(value || null);
        }
    },
    getValue: function() {
        var value = this.get('value');
        return value && value.clone();
    },
    setValueFromUi: function() {
        var value = this.$input.val() || false;
        this.setValue(this.parseClient(value));
    },
    setReadonly: function(readonly) {
        this.readonly = readonly;
        this.$input.prop('readonly', this.readonly);
    },
    isValid: function() {
        var value = this.$input.val();
        if(value === "") {
            return true;
        } else {
            try {
                this.parseClient(value);
                return true;
            } catch(e) {
                return false;
            }
        }
    },
    parseClient: function(v) {
        return field_utils.parse[this.type_of_date](v, null, {timezone: false});
    },
    formatClient: function(v) {
        return field_utils.format[this.type_of_date](v, null, {timezone: false});
    },
    setDatetimeDefault: function() {
        //when opening datetimepicker the date and time by default should be the one from
        //the input field if any or the current day otherwise
        var value;
        if(this.$input.val().length !== 0 && this.isValid()) {
            value = this.parseClient(this.$input.val());
        } else {
            value = moment().second(0);
        }

        this.picker.date(value);
    },
    changeDatetime: function() {
        if(this.isValid()) {
            this.setValueFromUi();
            this.trigger("datetime_changed");
        }
    },
    destroy: function() {
        this.picker.destroy();
        this._super.apply(this, arguments);
    },
});

var DateTimeWidget = DateWidget.extend({
    type_of_date: "datetime",
    init: function() {
        this._super.apply(this, arguments);
        this.options = _.defaults(this.options, {
            showClose: true,
        });
    },
});

return {
    DateWidget: DateWidget,
    DateTimeWidget: DateTimeWidget,
};

});
