global_javascript = """
<script>
function generateGradientColors(totalBars) {
    var palette = ['#d6488380', '#bb3f7c80', '#9f377580', '#842e6d80', '#68266680', '#4d1d5f80', '#52296b80', '#57367780', '#5c428480', '#614f9080', '#665b9c80', '#5e5f9980', '#56649580', '#4e689280', '#466d8e80', '#3e718b80', '#537e9280', '#688b9980', '#7e99a180', '#93a6a880', '#a8b3af80', '#95adaa80', '#82a7a580', '#6ea0a180', '#5b9a9c80', '#48949780'];
    var colors = [];
    var paletteSize = palette.length;
    var step = 1 / (totalBars + 1);

    for (var i = 0; i < totalBars; i++) {
        var index = Math.floor(i * paletteSize / totalBars) % paletteSize;
        colors.push(palette[index]);
    }
    return colors;
}
</script>
"""

def api_to_histplot(symptom):
    import requests
    base_url = "https://lesionbank.org/api/?type=symptom&symptom="
    response = requests.get(base_url + symptom)
    data = response.json()
    return genericHistPlot(data, "anatomical_name", "Count of Case Reports")

call_count = 0

def genericHistPlot(data, field, title=""):
    if title == "":
        title = f"Count of {field} Results"
    import json
    # Extract the required data from the JSON response
    fields = [item[field] for item in data]
    counts = {name: fields.count(name) for name in fields}

    # Prepare the data for the chart
    labels = list(counts.keys())
    values = list(counts.values())
    global call_count
    # Increment the call count
    call_count += 1
    # Reset the call count if it reaches 25
    if call_count == 25:
        call_count = 0
    
    id_name = f"myChart{field}_{call_count}"
    # JavaScript code to render the chart using Charts.js
    javascript_code = global_javascript + f"""
        <div>
            <canvas id="{id_name}"></canvas>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            var ctx = document.getElementById('{id_name}').getContext('2d');

            var colors = generateGradientColors({len(labels)})
            // Sort the labels and values in descending order based on values
            var sortedData = {json.dumps(sorted(zip(values, labels), reverse=True))}
            var sortedLabels = sortedData.map(item => item[1]);
            var sortedValues = sortedData.map(item => item[0]);

            var myChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: sortedLabels,
                    datasets: [{{
                        label: '{title}',
                        data: sortedValues,
                        backgroundColor: colors.slice(0, {len(labels)}),
                        borderColor: colors.slice(0, {len(labels)}),
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            precision: 0
                        }}
                    }}
                }}
            }});
        </script>
    """
    return javascript_code

call_count2 = 0
def genericBarChart(data, field, title=""):
    import json
    if title == "":
        title = f"{field} Results"
    
    # Extract the required data from the JSON response
    fields = [item[field] for item in data]
    averages = [item['avg'] for item in data]

    # Prepare the data for the chart
    labels = fields
    values = averages
    
    global call_count2
    # Increment the call count
    call_count2 += 1
    # Reset the call count if it reaches 25
    if call_count2 == 25:
        call_count2 = 0
    
    id_name = f"myBarChart_{field}_{call_count2}"
    
    javascript_code = global_javascript + f"""
        <div>
            <canvas id="{id_name}" class="{id_name}"></canvas>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            var elements = document.querySelectorAll('.' + '{id_name}');
            var lastElement = elements[elements.length - 1];
            var ctx = lastElement.getContext('2d');
            var colors = generateGradientColors({len(labels)})""" + f"""

            var myChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: '{title}',
                        data: {json.dumps(values)},
                        backgroundColor: colors.slice(0, {len(labels)}),
                        borderColor: colors.slice(0, {len(labels)}),
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    scales: {{
                        x: {{
                            ticks: {{
                                maxRotation: 90,
                                autoSkip: false
                            }}
                        }},
                        y: {{
                            beginAtZero: true,
                            precision: 0
                        }}
                    }}
                }}
            }});
        </script>
    """
    return javascript_code



def testPlot(rows, column_names):
    # Convert query result to a list of dictionaries
    results = []
    for row in rows:
        result = {}
        for i, column in enumerate(column_names):
            result[column] = row[i]
        results.append(result)
    # Convert the list of dictionaries to JSON
    return genericHistPlot(results, "symptom")

def queryToChart_improved(query, params, title="", field="symptom"):
    from . import genericFunctions
    results, column_names = genericFunctions.execute_query(query, params)

    # Convert query result to a list of dictionaries
    json_data = []
    for row in results:
        result = dict(zip(column_names, row))
        json_data.append(result)

    return genericBarChart(json_data, field, title)


def queryToChart(query, title="", field="symptom"):
    from . import genericFunctions
    results, column_names = genericFunctions.execute_query(query)

    # Convert query result to a list of dictionaries
    json_data = []
    for row in results:
        result = dict(zip(column_names, row))
        json_data.append(result)

    return genericBarChart(json_data, field, title)

from django.db import connection
from decimal import Decimal
import json

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

def queryToJson(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        data = cursor.fetchall()

    results = []
    for row in data:
        results.append(dict(zip(columns, row)))

    return json.dumps(results, cls=DecimalEncoder)

def jsonToErrorBar(jsonData):
    js_code = """
    <script src="https://unpkg.com/chart.js@4"></script>
    <script src="https://unpkg.com/chartjs-chart-error-bars@4"></script>
    <script>
        function parseData(jsonData) {
            const labelsX = jsonData.map(entry => entry.predicted_symptom);
            return [
                jsonData.map(entry => {
                    return {
                        y: entry.y,
                        yMin: entry.ymin,
                        yMax: entry.ymax,
                    };
                }),
                labelsX
            ];
        }
       
        const jsonDataErrorBar = """ + jsonData + """;
        const jsonParsed = parseData(jsonDataErrorBar);
        new Chart(document.getElementById('canvasErrorBar').getContext('2d'), {
            type: 'barWithErrorBars',
            data: {
                labels: jsonParsed[1],
                datasets: [{
                    data: jsonParsed[0],
                }],
            },
            options: {
                scales: {
                    y: {
                        ticks: {
                            beginAtZero: true,
                        },
                    },
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Chart Title',
                    },
                    legend: {
                        display: true,
                        labels: {
                            generateLabels: function(chart) {
                                return chart.data.datasets.map(function(dataset, i) {
                                    return {
                                        text: 'Mean t-Value ' + (i + 1),  // Generate custom labels for each dataset
                                        fillStyle: dataset.backgroundColor,
                                        strokeStyle: dataset.borderColor,
                                        lineWidth: dataset.borderWidth,
                                        hidden: !chart.isDatasetVisible(i),
                                        index: i
                                    };
                                });
                            }
                        }
                    },
                },
            },
        });

    </script>
    """

    html = """<div ><canvas id="canvasErrorBar"></canvas></div>"""

    return html + js_code

def jsonToBoxplot(jsonData):
    js_code = """
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <script>
        function convertDataBox(jsonData) {
            return jsonData.map(entry => {
                const data = [
                entry.min_t_stat,
                entry.q25,
                entry.median,
                entry.q75,
                entry.max_t_stat
                ];

                return {
                x: entry.predicted_symptom,
                y: data
                };
            });
        }
        function convertDataScatter(jsonData) {
            return jsonData.map(entry => {
                return {
                x: entry.predicted_symptom,
                y: entry.avg
                };
            });
        }
        function createBoxplot(jsonData) {
            const data = convertDataBox(jsonData);
            const scatterData = convertDataScatter(jsonData);
            var options = {
                series: [
                    {
                        name: 'Distribution',
                        type: 'boxPlot',
                        data: data,
                    },
                    {
                        name: 'Mean',
                        type: 'scatter',
                        data: scatterData,
                    }
                ],
                chart: {
                    selection: {
                        enabled: false // Disable selection
                    },
                    type: 'boxPlot',
                    height: 350,
                    toolbar: {
                        show: false,
                        tools: {
                            download: false
                        }
                    },
                },
                colors: ['#008FFB', '#FEB019'],
                title: {
                    text: 'BoxPlot Chart',
                    align: 'left'
                }, 
            };
            var chart = new ApexCharts(document.querySelector("#boxPlot"), options);
            chart.render();
        }
        const jsonData = """ + jsonData + """;
        createBoxplot(jsonData);
    </script>
    """
    return """<div  id="boxPlot"></div>""" + js_code

def page(request):
    from django.http import HttpResponse
    import json
    if request.GET:
        boxplot = request.GET.get('boxplot', False)
        if boxplot:
            response = jsonToBoxplot(queryToJson("""select * from lesion_predictions_distribution
                where lesion_id = %(lesion_id)s;""", {'lesion_id': 26})) + jsonToErrorBar(queryToJson("""select predicted_symptom, avg as y, avg-stddev as yMin, avg+stddev as yMax from lesion_predictions_distribution
                where lesion_id = %(lesion_id)s;""", {'lesion_id': 26}))
            return HttpResponse( response )
        symptom = request.GET.get('symptom', False)
        if symptom:
            return HttpResponse(api_to_histplot(symptom))