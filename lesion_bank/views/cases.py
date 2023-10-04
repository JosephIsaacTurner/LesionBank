from django.http import HttpResponse, HttpRequest
from . import genericFunctions
from . import charts
from django.shortcuts import render


def cases_view(request):
    
    query = """SELECT CONCAT('<option class="dropdown-item" value="', lesion_id, '">', ROW_NUMBER() OVER (ORDER BY author), ': ', Author, ' (', Symptom, ') </option>') AS "Author (Symptom)" 
            FROM lesiontable 
            ORDER BY author;"""
    dropdownList = ""
    column_names, rows = genericFunctions.execute_query(query)
    for row in rows:
        for value in row:
            dropdownList += value
    query = """SELECT CONCAT('<a href="../cases?id=', Lesion_Id, '">', Author, '</a>' ) as "Lesion Info", string_agg(DISTINCT symptom, ', ' ORDER BY symptom) AS "Symptoms Present"
                    FROM lesiontable
                    GROUP BY author, lesion_id
                    """
    fullList = genericFunctions.query_to_table(query, "list")
    if not request.GET:
        return render(request, 'lesion_bank/cases_list.html',{'title': "Case Reports",'dropdownList':dropdownList,'fullList':fullList})
    
    lesionId = request.GET.get('id')
    authorCoordQuery = f"""
    select 
        concat(mode_x, ', ', mode_y, ', ', mode_z) as coordinate
        , author
    from (
        SELECT
            (SELECT x FROM tracingscoordinates WHERE lesion_id = '{lesionId}' GROUP BY x ORDER BY COUNT(*) DESC LIMIT 1) AS mode_x
            , (SELECT y FROM tracingscoordinates WHERE lesion_id = '{lesionId}' GROUP BY y ORDER BY COUNT(*) DESC LIMIT 1) AS mode_y
            , (SELECT z FROM tracingscoordinates WHERE lesion_id = '{lesionId}' GROUP BY z ORDER BY COUNT(*) DESC LIMIT 1) AS mode_z
            , author
        from lesiontable
        where lesion_id = '{lesionId}'
        ) as innerquery
    """
    returnedValues = genericFunctions.fetch_single_row(authorCoordQuery)
    author = returnedValues["author"]
    startingcoord = returnedValues["coordinate"].split(",")
    
    authorQuery = f"""
    select
        lesion_id 
        , concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as "lesion info"
        , symptom
        , tracing_file_name
        , network_file_name
    from LesionTable
    where lesion_id = '{lesionId}'
    """
    authorLesions = genericFunctions.query_to_table(authorQuery, "tracing", True)
    authorNetworks = genericFunctions.query_to_table(authorQuery, "network", True)
    # lesionConnectivityChart = charts.queryToChart(f"select predicted_symptom, average as avg from lesion_predictions where lesion_id = {lesionId}", "Average Symptom Connectivity", "predicted_symptom")
    # lesionConnectivityChart2 = charts.jsonToBoxplot(charts.queryToJson("""select * from lesion_predictions_distribution where lesion_id = %(lesion_id)s;""", {'lesion_id': lesionId}))
    lesionConnectivityChart3 = charts.jsonToErrorBar(charts.queryToJson("""select predicted_symptom, avg as y, avg-stddev as yMin, avg+stddev as yMax from lesion_predictions_distribution
        where lesion_id = %(lesion_id)s;""", {'lesion_id': lesionId}))

    return render(request, 'lesion_bank/cases.html',{'title': "Case Reports",
                                                        'lesionId':lesionId,
                                                        'dropdownList':dropdownList,
                                                        'author':author,
                                                        'authorLesions':authorLesions,
                                                        'authorNetworks':authorNetworks,
                                                        'lesionConnectivityChart3':lesionConnectivityChart3,
                                                        'initial_coord_1':startingcoord[0],
                                                        'initial_coord_2':startingcoord[1],
                                                        'initial_coord_3':startingcoord[2]})

# pageStyles = """
#      <!-- Styles -->
#         <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css' rel='stylesheet'>
#         <script src='https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js'></script>
#         <link rel='stylesheet' type='text/css' href='../static/css/papaya.css?version=0.8&build=979' />
#     	<script type='text/javascript' src='../static/papaya.js?version=0.8&build=979'></script>
#         <style>
#         .myTooltip {
#             position: absolute;
#             background-color: black;
#             color: white;
#             padding: 5px;
#             font-size: 12px;
#             border-radius: 3px;
#             white-space: nowrap;
#         }
#         .papaya-container {
#             overflow: hidden;
#         }
#         .list-group-item.active{
#             border: none;
#         }
#         </style>
# """

# def getDynamicContent(lesionId):
#     authorCoordQuery = f"""
#     select 
#         concat(mode_x, ', ', mode_y, ', ', mode_z) as coordinate
#         , author
#     from (
#         SELECT
#             (SELECT x FROM tracingscoordinates WHERE lesion_id = '{lesionId}' GROUP BY x ORDER BY COUNT(*) DESC LIMIT 1) AS mode_x
#             , (SELECT y FROM tracingscoordinates WHERE lesion_id = '{lesionId}' GROUP BY y ORDER BY COUNT(*) DESC LIMIT 1) AS mode_y
#             , (SELECT z FROM tracingscoordinates WHERE lesion_id = '{lesionId}' GROUP BY z ORDER BY COUNT(*) DESC LIMIT 1) AS mode_z
#             , author
#         from lesiontable
#         where lesion_id = '{lesionId}'
#         ) as innerquery
#     """
#     returnedValues = genericFunctions.fetch_single_row(authorCoordQuery)
#     author = returnedValues["author"]
#     startingcoord = returnedValues["coordinate"]

#     authorQuery = f"""
#     select
#         lesion_id 
#         , concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as "lesion info"
#         , symptom
#         , tracing_file_name
#         , network_file_name
#     from LesionTable
#     where lesion_id = '{lesionId}'
#     """
#     authorLesions = genericFunctions.query_to_table(authorQuery, "tracing", True)
#     authorNetworks = genericFunctions.query_to_table(authorQuery, "network", True)
#     lesionConnectivityChart = charts.queryToChart(f"select predicted_symptom, average as avg from lesion_predictions where lesion_id = {lesionId}", "Average Symptom Connectivity", "predicted_symptom")
#     lesionConnectivityChart2 = charts.jsonToBoxplot(charts.queryToJson("""select * from lesion_predictions_distribution where lesion_id = %(lesion_id)s;""", {'lesion_id': lesionId}))
#     lesionConnectivityChart3 = charts.jsonToErrorBar(charts.queryToJson("""select predicted_symptom, avg as y, avg-stddev as yMin, avg+stddev as yMax from lesion_predictions_distribution
#         where lesion_id = %(lesion_id)s;""", {'lesion_id': lesionId}))

#     javascript = genericFunctions.getJavascript(startingcoord)
#     htmlString = f"""
#     {pageStyles}
#     <div class='container'>
#         <div class="card card-body">
#             <div class="row">
#                 <div id='papayaHolder' class='papayaHolder col-sm-6'>
#                     <div class='papaya' id='papaya1' data-params='params'></div>
#                     <div style='padding: 10px;' class='input-group mb-3' id='selectedCoordinate'>
#                                 <button id='questionButton1' type="button" data-bs-placement="bottom" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-title="Coordinate Navigator:" data-bs-content="Drag the crosshairs or enter a coordinate to navigate to a specific location in the visualizer. Click 'Find what's here' to search our lesion dataset based on the active coordinate.">
#                                     <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                         <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                         <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                     </svg>
#                                 </button>
#                                 <span class="input-group-text bg-secondary bg-gradient">Navigator: </span>
#                                 <span class="input-group-text">X</span>
#                                 <input type="text" class="form-control selectCoord" placeholder="X" id='findX' aria-label="X" >
#                                 <span class="input-group-text">Y</span>
#                                 <input type="text" class="form-control selectCoord" placeholder="Y" id='findY' aria-label="Y" >
#                                 <span class="input-group-text">Z</span>
#                                 <input type="text" class="form-control selectCoord" placeholder="Z" id='findZ' aria-label="Z" >
#                                 <a class="btn btn-outline-secondary" type="button" id='findS' >Find what's here</a>
#                             </div>                </div> 
#                 <div class='col-sm-6'>
#                     <div class='card'>
#                         <div class="card-header">
#                             <h3 class='card-title'>Results for {author}:</h3>
#                         </div>
                        
#                         <ul class="nav nav-tabs bg-body" id="myTab" role="tablist">
#                             <li class="nav-item bg-body border-bottom-0" role="presentation">
#                                 <button class="nav-link active " id="home-tab" data-bs-toggle="tab" data-bs-target="#home" type="button" role="tab" aria-controls="home" aria-selected="true">Lesion Case Reports</button>
#                             </li>
#                             <li class="nav-item bg-body" role="presentation">
#                                 <button class="nav-link" id="profile-tab" data-bs-toggle="tab" data-bs-target="#profile" type="button" role="tab" aria-controls="profile" aria-selected="false">Lesion Network Maps</button>
#                             </li>
#                         </ul>


#                         <div class="tab-content list-group list-group-flush " id="myTabContent">
#                             <div class="list-group-item border-0 bg-body border-danger" style='display:none; --bs-list-group-active-border-color: unset !important;' ></div>
#                             <div class=" tab-pane fade show active list-group-item bg-body" id="home" role="tabpanel" aria-labelledby="home-tab">
                        
#                                 <h6 class="card-subtitle mb-2 text-muted"> Lesions for {author}:
#                                     &nbsp;&nbsp;
#                                     <button id='questionButton3' type="button" data-bs-placement="right" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Lesion tracing:" 
#                                     data-bs-content="The lesion tracing (an overlay of the lesioned brain area) for the lesion case report is shown here. 
#                                     <br><br> You may click on the symptom name to search our dataset for all lesions and network maps involving the specified symptom.
#                                     <br><br>To load results as overlays on the viewer, toggle the view icons to the right.">
#                                                                         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                                                             <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                                                             <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                                                         </svg>
#                                     </button>
#                                 </h6>
#                                 {authorLesions} 
                        
#                             </div>

#                             <div class="tab-pane fade list-group-item bg-body border-0" id="profile" role="tabpanel" aria-labelledby="profile-tab">
#                                 <h6 class="card-subtitle mb-2 text-muted">Lesion network maps for {author}:
#                                     &nbsp;&nbsp;
#                                     <button id='questionButton4' type="button" data-bs-placement="right" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Lesion network maps:" 
#                                     data-bs-content="The lesion network map for the selected lesion case report is displayed here. You may click on the symptom name to search our dataset for all lesions and network maps involving the specified symptom. 
#                                     <br><br>The lesion network map is a heatmap of brain areas that are functionally connected to the lesioned anatomy.
#                                     <br><br>To load results as overlays on the viewer, toggle the respective view icons to the right.">
#                                         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                             <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                             <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                         </svg>
#                                     </button>
#                                 </h6>
#                                 {authorNetworks}
#                             </div>
#                             {lesionConnectivityChart}
#                             {lesionConnectivityChart2}
#                             {lesionConnectivityChart3}                            
#                         </div>
#                     </div>
#                 </div>
#             </div>
#         </div>
#     </div>
#     {javascript}
#     """
#     return htmlString
# def cases_view_old(request):
#     query = """SELECT CONCAT('<option class="dropdown-item" value="', lesion_id, '">', ROW_NUMBER() OVER (ORDER BY author), ': ', Author, ' (', Symptom, ') </option>') AS "Author (Symptom)" 
#             FROM lesiontable 
#             ORDER BY author;"""
#     dropdownList = ""
#     column_names, rows = genericFunctions.execute_query(query)
#     for row in rows:
#         for value in row:
#             dropdownList += value

#     if request.GET:
#         # author = request.GET.get('author')
#         lesionId = request.GET.get('id')
#         dynamicContent = f"""<div class='container'>
                            
#                                     <form method='_GET'>
#                                                 <div class="input-group mb-3  input-group-lg">
#                                                     <select id='selectMenu'class='form-select' aria-label='Select an option' name='id'>
#                                                     {dropdownList} 
#                                                     </select> 
#                                                     <script>
#                                                         const symptom = "{lesionId}" // get the value of the symptom variable
#                                                         const selectMenu = document.getElementById("selectMenu") // get the select element
#                                                         // loop through the options and set the "selected" attribute to the corresponding option
#                                                         for (let i = 0; i < selectMenu.options.length; i++)""" + """ {
#                                                             if (selectMenu.options[i].value === symptom) {
#                                                                 selectMenu.options[i].selected = true
#                                                             }
#                                                         } """ + f"""
#                                                     </script>
#                                                     <button class="btn btn-outline-secondary" type="submit" id="button-addon1">Select</button>
#                                                 </div>
#                                     </form>
                            
#                             </div>"""
#         dynamicContent += getDynamicContent(lesionId)
#     else:
#         query = """SELECT CONCAT('<a href="../cases?id=', Lesion_Id, '">', Author, '</a>' ) as "Lesion Info", string_agg(DISTINCT symptom, ', ' ORDER BY symptom) AS "Symptoms Present"
#                 FROM lesiontable
#                 GROUP BY author, lesion_id
#                 """
#         dynamicContent = genericFunctions.query_to_table(query, "list")
#         dynamicContent += genericFunctions.getJavascript()
#         dynamicContent = f"""<div class='container'>
#                                 <div class="card">
#                                     <div class="card-header">
#                                         <br>
#                                         <h4 class="card-subtitle mb-2 text-muted"> Select an author to view lesion maps for each case in our database:</h4>
#                                             <form method='_GET'>
#                                                 <div class="input-group mb-3  input-group-lg">
#                                                     <select class='form-select' aria-label='Select an option' name='author'>
#                                                     {dropdownList} 
#                                                     </select> 
#                                                     <button class="btn btn-outline-secondary" type="submit" id="button-addon1">Select</button>
#                                                 </div>
#                                             </form>
#                                     </div>
#                                     <!-- <div class="w-75">
#                                         <button class="btn btn-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#collapseExample" aria-expanded="false" aria-controls="collapseExample">
#                                             Toggle Table View
#                                         </button>
#                                     </div>
#                                     -->
#                                     <!-- <div class="collapse" id="collapseExample"> -->
#                                         <div class="card card-body">
#                                             <h3 class='card-subtitle mb-2 text-muted'>All Authors</h3>
#                                             {dynamicContent}
#                                         </div>
#                                     <!-- </div> -->                                   
#                                 </div>
#                             </div>
#                             <br><br>"""
#     html_string = genericFunctions.getHTMLString()
#     html_string = html_string.replace("%%REPLACE_ME%%", dynamicContent).replace("casesActive", "active").replace("%%REPLACE_PAGE_NAME%%", "Case Reports")
#     return HttpResponse(html_string)