odoo.define('marketing_automation.activity_graph', function (require) {
'use strict';

var BasicFields = require('web.basic_fields');
var registry = require('web.field_registry');


var ActivityGraph = BasicFields.JournalDashboardGraph.extend({
    className: 'o_ma_activity_graph',
    /**
     * @private
     * @override _render from JournalDashboardGraph
     */
    _render: function () {
        var self = this;
        this.chart = null;
        this.$el.empty().append('<svg>');
        nv.addGraph(function () {
            var indexMap = _.map(self.data[0].values, function (d) {
                return d.x;
            });
            self.chart = nv.models.lineChart().useInteractiveGuideline(true);
            self.chart.forceY([0]);
            self.chart.options({
                x: function (d) { return indexMap.indexOf(d.x); },
                margin: {'left': 25, 'right': 20, 'top': 5, 'bottom': 20},
                showYAxis: false,
                showLegend: false
            });
            self.chart.xAxis.tickFormat(function (d) {
                var label = '';
                _.each(self.data, function (v) {
                    if (v.values[d] && v.values[d].x) {
                        label = v.values[d].x;
                    }
                });
                return label;
            });

            d3.select(self.$('svg')[0])
                .datum(self.data)
                .transition().duration(1200)
                .call(self.chart);

            window.dispatchEvent(new Event('resize'));
        });
    }
});

registry.add('marketing_automation_activity_graph', ActivityGraph);

return ActivityGraph;

});
