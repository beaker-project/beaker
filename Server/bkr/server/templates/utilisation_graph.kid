<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>Utilisation graph</title>
    <script type="text/javascript" src="${tg.url('/static/javascript/date.f-0.5.0.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.flot-r323.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.flot-r323.stack.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.flot-r323.selection.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.flot-r323.crosshair.js')}"></script>
    <!-- until flot gains axis label support: http://code.google.com/p/flot/issues/detail?id=42 -->
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.flot.axislabels-git.5ab8185b.js')}"></script>
    <style type="text/css">
        div#fedora-content {
            padding: 0 1.5em 1.5em 1.5em;
        }
        .loading-message {
            background-color: #ececec;
            border: 1px solid #777777;
            text-align: center;
            display: table-cell;
            height: 100%;
            vertical-align: middle;
        }
        #graph-control fieldset {
            display: inline;
        }
        #graph-control div select {
            display: block;
            margin: 0.5em 0 0.5em 2em;
        }
        #graph-control button {
            margin-top: 0.5em;
        }
        #beside-graph {
            width: 20em;
            position: absolute;
            left: 1050px; /* XXX actually 1000px + 1.5em + padding */
        }

        .about {
            max-width: 40em;
        }
        .about dl {
            margin-left: 2em;
        }
        .about dl dt {
            margin-top: 0.5em;
        }
    </style>
    <script type="text/javascript">
        //<![CDATA[
        function UtilisationGraph(legend_div, date_div, graph_div, overview_div, control_form) {
            this.legend_div = legend_div;
            this.date_div = date_div;
            this.graph_div = graph_div;
            this.overview_div = overview_div;
            this.control_form = control_form;
            var graph = this;
            $(this.date_div).html(
                    '<p>Date range:<br/><span class="range"/></p>' +
                    '<p>Hovering at:<br/><span class="hover"/></p>');
            $(this.control_form).bind('submit', function () {
                graph._update_overview();
                graph._update_graph();
                return false;
            });
            $(this.graph_div).bind('plotselected', function (event, ranges) {
                graph.selection_start = Math.floor(ranges.xaxis.from);
                graph.selection_end = Math.floor(ranges.xaxis.to);
                if (graph.overview_plot) {
                    graph.overview_plot.setSelection(ranges, true);
                }
                graph._update_graph();
                graph._update_date_range();
            });

            // based on http://people.iola.dk/olau/flot/examples/tracking.html
            var latest_position = null, update_legend_timeout = null;
            var update_legend = function () {
                var pos = latest_position;
                update_legend_timeout = null;
                var dataset = graph.plot.getData();
                var legend_labels = $('.legendLabel', graph.legend_div);
                var point;
                for (var i = 0; i < dataset.length; i ++) {
                    var series = dataset[i];
                    for (var j = 0; j < series.data.length; j ++) {
                        if (series.data[j][0] > pos.x)
                            break;
                    }
                    point = series.data[Math.max(0, j - 1)];
                    legend_labels.eq(i).text(series.label + ' = ' + point[1]);
                }
                $('span.hover', graph.date_div).text(new Date(point[0]).f('yyyy-MM-dd HH:MM'));
            };
            $(this.graph_div).bind('plothover', function (event, pos, item) {
                latest_position = pos;
                if (!update_legend_timeout)
                    update_legend_timeout = setTimeout(update_legend, 50);
            });

            $(this.overview_div).bind('plotselected', function (event, ranges) {
                graph.selection_start = Math.floor(ranges.xaxis.from);
                graph.selection_end = Math.floor(ranges.xaxis.to);
                graph._update_graph();
                graph._update_date_range();
            });
            this._update_overview();
            this._update_graph();
        }
        UtilisationGraph.prototype._update_graph = function () {
            var graph = this;
            this.plot = undefined;
            $(this.graph_div).addClass('loading-message').html('Loading...');
            var options = $(this.control_form).serializeArray();
            if (this.selection_start && this.selection_end)
                options = options.concat([
                        {name: 'start', value: this.selection_start},
                        {name: 'end', value: this.selection_end}]);
            if (this.pending_graph_ajax)
                this.pending_graph_ajax.abort();
            this.pending_graph_ajax = $.ajax({
                url: 'utilisation_timeseries',
                data: options,
                dataType: 'json',
                success: function (result) {
                    graph.pending_graph_ajax = undefined;
                    graph._draw_graph(result);
                },
                error: function (xhr) {
                    if (xhr.statusText != 'abort') {
                        console.log(xhr);
                        graph._error(xhr);
                    }
                }
            });
            $('a.csv-download').attr('href', 'utilisation_timeseries?' +
                    $.param(options.concat([{name: 'tg_format', value: 'csv'}])));
        };
        UtilisationGraph.prototype._update_overview = function () {
            var graph = this;
            this.overview_plot = undefined;
            $(this.overview_div).addClass('loading-message').html('Loading...');
            var options = $(this.control_form).serializeArray();
            if (this.pending_overview_ajax)
                this.pending_overview_ajax.abort();
            this.pending_overview_ajax = $.ajax({
                url: 'existence_timeseries',
                data: options,
                dataType: 'json',
                success: function (result) {
                    graph.pending_overview_ajax = undefined;
                    graph._draw_overview(result);
                },
                error: function (xhr) {
                    if (xhr.statusText != 'abort') {
                        console.log(xhr);
                        graph._error(xhr);
                    }
                }
            });
        };
        UtilisationGraph.prototype._update_date_range = function () {
            var series = this.overview_plot.getData()[0];
            var start = this.selection_start || series.data[0][0];
            var end = this.selection_end || series.data[series.data.length - 1][0];
            $('span.range', this.date_div).text(
                    new Date(start).f('yyyy-MM-dd HH:MM') +
                    ' to ' +
                    new Date(end).f('yyyy-MM-dd HH:MM'));
        };
        UtilisationGraph.prototype._error = function (xhr) {
            $(this.graph_div).html('<div class="error">Error loading data!</div>')
                    .append(xhr.responseXML);
        };
        UtilisationGraph.prototype._draw_graph = function (result) {
            $(this.graph_div).removeClass('loading-message');
            this.plot = $.plot(this.graph_div,
                    [{data: result['manual'], label: 'manual', lines: {show: true, fill: true}},
                     {data: result['recipe'], label: 'recipe', lines: {show: true, fill: true}},
                     {data: result['idle_broken'], label: 'idle (broken)', lines: {show: true, fill: true}},
                     {data: result['idle_manual'], label: 'idle (manual)', lines: {show: true, fill: true}},
                     {data: result['idle_automated'], label: 'idle (automated)', lines: {show: true, fill: true}}],
                    {xaxis: {mode: 'time'},
                     yaxis: {axisLabel: 'Systems'},
                     series: {stack: true},
                     selection: {mode: 'x'},
                     grid: {hoverable: true, autoHighlight: false},
                     crosshair: {mode: 'x'},
                     legend: {container: this.legend_div}});
        };
        UtilisationGraph.prototype._draw_overview = function (result) {
            $(this.overview_div).removeClass('loading-message');
            this.overview_plot = $.plot(this.overview_div,
                    [{data: result['cum_freqs']}],
                    {xaxis: {mode: 'time'},
                     yaxis: {ticks: [], axisLabel: 'Systems'},
                     series: {lines: {show: true, lineWidth: 1}, shadowSize: 0},
                     selection: {mode: 'x'}});
            if (this.selection_start && this.selection_end)
                this.overview_plot.setSelection({xaxis:
                        {from: this.selection_start, to: this.selection_end}}, true);
            this._update_date_range();
        };
        $(function () {
            graph = new UtilisationGraph($('#graph-legend').get(0),
                    $('#date-readout').get(0),
                    $('#graph').get(0),
                    $('#overview-graph').get(0),
                    $('#graph-control').get(0));
            $('form#graph-control input:checkbox[id^="enable_"]')
                .each(function (i, elem) {
                    var target = $('#' + elem.id.substring(7));
                    $(elem).change(function () {
                        if (elem.checked) {
                            target.show('slow');
                            target.removeAttr('disabled');
                        } else {
                            target.hide('fast');
                            target.attr('disabled', true);
                        }
                    });
                    if (!elem.checked) {
                        target.hide();
                        target.attr('disabled', true);
                    }
                });
        });
    //]]>
    </script>
</head>

<body class="flora">
<h1>Utilisation graph</h1>
<form id="graph-control" action="#">
<!--! XXX re-use system search bar here instead? -->
<fieldset>
    <legend>System filtering options</legend>
    <div>
        <input type="checkbox" id="enable_arch_id" />
        <label for="enable_arch_id">Arch</label>
        <select id="arch_id" name="arch_id" multiple="multiple" size="8">
            <option py:for="id, name in all_arches" value="${id}">${name}</option>
        </select>
    </div>
    <div>
        <input type="checkbox" id="enable_group_id" />
        <label for="enable_group_id">Group</label>
        <select id="group_id" name="group_id" multiple="multiple" size="8">
            <option value="-1">(none)</option>
            <option py:for="id, name in all_groups" value="${id}">${name}</option>
        </select>
    </div>
    <div>
        <input type="checkbox" id="only_shared" name="only_shared" />
        <label for="only_shared">Only shared systems</label>
    </div>
    <div><button type="submit">Update graph options</button></div>
</fieldset>
</form>
<p>Drag a region on the graph or on the timeline to zoom.
Hover over the graph for details.
You can <a class="csv-download">download this data as CSV</a>.</p>
<div id="beside-graph">
    <div id="graph-legend" />
    <div id="date-readout" />
</div>
<div id="graph" style="width: 1000px; height: 300px;"/>
<div id="overview-graph" style="width: 800px; height: 75px; margin: 1em 100px 0 100px;"/>

<div class="about">
<h2>About this report</h2>
<p>This graph shows historical data about the number of systems in Beaker and 
how they are being used. The data series on the graph are defined as 
follows:</p>
<dl>
    <dt>manual</dt>
    <dd>Systems which are manually reserved (by using "Take" in the web UI)</dd>
    <dt>recipe</dt>
    <dd>Systems running a recipe under the control of the scheduler</dd>
    <dt>idle (broken)</dt>
    <dd>Systems which are not in use, and whose condition is set to "Broken"</dd>
    <dt>idle (manual)</dt>
    <dd>Systems which are not in use, and are not available for scheduling (condition set to "Manual")</dd>
    <dt>idle (automated)</dt>
    <dd>Systems which are not in use, and are available for scheduling (condition set to "Automated")</dd>
</dl>
</div>
</body>
</html>
