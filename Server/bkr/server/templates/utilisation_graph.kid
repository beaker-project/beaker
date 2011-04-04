<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>Utilisation graph</title>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery-1.5.1.min.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.flot-r323.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.flot-r323.stack.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.flot-r323.selection.js')}"></script>
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
        #graph-control span {
            padding-right: 1em;
        }
        #graph-legend {
            width: 10em;
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
        function UtilisationGraph(legend_div, graph_div, overview_div, control_form) {
            this.legend_div = legend_div;
            this.graph_div = graph_div;
            this.overview_div = overview_div;
            this.control_form = control_form;
            var graph = this;
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
            });
            $(this.overview_div).bind('plotselected', function (event, ranges) {
                graph.selection_start = Math.floor(ranges.xaxis.from);
                graph.selection_end = Math.floor(ranges.xaxis.to);
                graph._update_graph();
            });
            this._update_overview();
            this._update_graph();
        }
        UtilisationGraph.prototype._update_graph = function () {
            var graph = this;
            this.plot = undefined;
            $(this.graph_div).addClass('loading-message').html('Loading...');
            var options = $(this.control_form).serializeArray();
            if (this.selection_start &amp;&amp; this.selection_end)
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
        UtilisationGraph.prototype._error = function (xhr) {
            $(this.graph_div).html('&lt;div class="error"&gt;Error loading data!&lt;/div&gt;')
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
                     series: {stack: true},
                     selection: {mode: 'x'},
                     legend: {container: this.legend_div}});
        };
        UtilisationGraph.prototype._draw_overview = function (result) {
            $(this.overview_div).removeClass('loading-message');
            this.overview_plot = $.plot(this.overview_div,
                    [{data: result['cum_freqs']}],
                    {xaxis: {mode: 'time'},
                     yaxis: {ticks: []},
                     series: {lines: {show: true, lineWidth: 1}, shadowSize: 0},
                     selection: {mode: 'x'}});
            if (this.selection_start &amp;&amp; this.selection_end)
                this.overview_plot.setSelection({xaxis:
                        {from: this.selection_start, to: this.selection_end}}, true);
        };
        $(function () {
            graph = new UtilisationGraph($('#graph-legend').get(0),
                    $('#graph').get(0),
                    $('#overview-graph').get(0),
                    $('#graph-control').get(0));
        });
    </script>
</head>

<body class="flora">
<h1>Utilisation graph</h1>
<form id="graph-control" action="#">
<p>
    <span>
        <label for="arch_id">Arch:</label>
        <select id="arch_id" name="arch_id">
            <option py:for="id, name in all_arches" value="${id}">${name}</option>
        </select>
    </span>
    <span>
        <input type="checkbox" id="shared_no_groups" name="shared_no_groups" />
        <label for="shared_no_groups">Only shared systems with no groups</label>
    </span>
    <span><input type="submit" value="Update graph options" /></span>
</p>
</form>
<div id="graph-legend" />
<div id="graph" style="width: 1000px; height: 300px;"/>
<div id="overview-graph" style="width: 800px; height: 75px; margin: 1em 100px 0 100px;"/>
<p><a class="csv-download">Download this data as CSV</a></p>

<div class="about">
<h2>About this report</h2>
<p>This graph shows historical data about the number of systems recorded in 
Beaker and how they are being used. The y-axis represents the count of systems, 
the x-axis represents time. Drag on the graph to select a time period to zoom in 
on.</p>
<p>The data series on the graph are defined as follows:</p>
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
