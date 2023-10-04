from django.http import HttpResponse, HttpRequest
from . import genericFunctions
from . import charts
from django.shortcuts import render
from django.db import connection
from django.conf import settings
private_symptoms = settings.PRIVATE_SYMPTOMS


def run_raw_sql(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        # Fetch the column names from the cursor description
        column_names = [col[0] for col in cursor.description]
        return [
            dict(zip(column_names, row))
            for row in cursor.fetchall()
    ]

def symptoms_view(request):
    context = {}
    min_count = 5
    query = f"""select * from (
                    select symptom, count(metadata.lesion_id) as "count" from symptoms
                    left join metadata_symptoms 
                    on metadata_symptoms.symptoms_id = symptoms.id
                    left join metadata on metadata.lesion_id = metadata_symptoms.lesionmetadata_id
                    group by symptom) as a 
                where a."count" > {min_count}"""
    if not request.user.is_authenticated:
        query += f""" AND symptom NOT IN ({', '.join(map(lambda x: f"'{x}'", private_symptoms))})"""
    query += " ORDER BY symptom"
    symptom_list = ""
    symptom_list = run_raw_sql(query)
    context['title'] = "Symptoms"
    context['symptom_list'] =  symptom_list
    context['min_count'] = min_count
    return render(request, 'lesion_bank/all_symptoms.html', context)




    # query = """SELECT distinct CONCAT('<option class="dropdown-item" value="', symptom, '">', ROW_NUMBER() OVER (ORDER BY symptom), ': ', Symptom, '</option>') AS symptom 
    #         FROM (select distinct symptom from lesiontable
    #             ) as subqery
    #         order by symptom"""
    # dropdownList = ""
    # column_names, rows = genericFunctions.execute_query(query)
    # for row in rows:
    #     for value in row:
    #         dropdownList += value

    # if not request.GET:
    #     query = """SELECT distinct symptom FROM lesiontable"""
    #     symptomList = genericFunctions.query_to_table(query, "list")

    #     return render(request, 'lesion_bank/symptom_list.html',{'title': "Symptoms",'dropdownList':dropdownList,'symptomList':symptomList})
    # symptom = request.GET.get('symptom')
    # avg_query = f"""
    #         select 
    #             anatomical_name
    #             , avg_tstat as avg
    #         from avg_t_stat_location
    #         inner join atlaskey
    #         on atlaskey.locationid = avg_t_stat_location.locationid
    #         WHERE avg_t_stat_location.symptom = '{symptom}'
    #         order by avg desc
    #     """
    # chart = f"""
    #         <div>
    #         <br><br>
    #             {charts.api_to_histplot(symptom)}
    #         <br>
    #             {charts.queryToChart(avg_query, "Average T_Stat Value", "anatomical_name")}
    #         </div>
    #     """
    # # symptomQuery = f"select * from lesiontable where symptom = '{symptom}'"
    # symptomQuery = f"""
    # select
    #     lesion_id 
    #     , concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as "lesion info"
    #     , symptom
    #     , tracing_file_name
    #     , network_file_name
    # from LesionTable
    # where symptom = '{symptom}'
    # """
    # symptomLesions = genericFunctions.query_to_table(symptomQuery, "tracing", True)
    # symptomNetworks = genericFunctions.query_to_table(symptomQuery, "network", True)
    # return render(request, 'lesion_bank/symptoms.html',{'title': "Symptoms",
    #                                                     'dropdownList':dropdownList,
    #                                                     'symptom':symptom,
    #                                                     'symptomLesions':symptomLesions,
    #                                                     'symptomNetworks':symptomNetworks,
    #                                                     'chart':chart,
    #                                                     'initial_coord_1':0,
    #                                                     'initial_coord_2':0,
    #                                                     'initial_coord_3':0})

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

# def getDynamicContent(symptom):
#     avg_query = f"""
#         select 
#             anatomical_name
#             , avg_tstat as avg
#         from avg_t_stat_location
#         inner join atlaskey
#         on atlaskey.locationid = avg_t_stat_location.locationid
#         WHERE avg_t_stat_location.symptom = '{symptom}'
#         order by avg desc
#     """
#     chart = f"""
#             <div>
#             <br><br>
#                 {charts.api_to_histplot(symptom)}
#             <br>
#                 {charts.queryToChart(avg_query, "Average T_Stat Value", "anatomical_name")}
#             </div>
#         """
#     # symptomQuery = f"select * from lesiontable where symptom = '{symptom}'"
#     symptomQuery = f"""
#     select
#         lesion_id 
#         , concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as "lesion info"
#         , symptom
#         , tracing_file_name
#         , network_file_name
#     from LesionTable
#     where symptom = '{symptom}'
#     """
#     symptomLesions = genericFunctions.query_to_table(symptomQuery, "tracing", True)
#     symptomNetworks = genericFunctions.query_to_table(symptomQuery, "network", True)
#     javascript = genericFunctions.getJavascript(0,0,0)
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
#                             </div>
#                 </div> 
#                 <div class='col-sm-6'>
#                     <div class='card'>
#                         <div class="card-header">
#                             <h3 class='card-title'>
#                             <button id='questionButton2' type="button" data-bs-placement="left" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Results:" data-bs-content="
#                                 All lesion case studies and lesion network maps associated with the selected symptom are displayed here.">
#                                         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                             <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                             <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                         </svg>
#                             </button>
#                             Results for {symptom}:</h3>
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
                        
#                                 <h6 class="card-subtitle mb-2 text-muted"> Lesions for {symptom}:
#                                     &nbsp;&nbsp;
#                                     <button id='questionButton3' type="button" data-bs-placement="right" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Lesion matches:" 
#                                         data-bs-content="Any lesions found within the search parameters are listed here. 
#                                         <br><br> You may click on the author's name to be redirected to a new page that contains more detailed information on the specific case in question. 
#                                         <br><br>To load results as overlays on the viewer, toggle the view icons to the right.">
#                                                                         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                                                             <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                                                             <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                                                         </svg>
#                                     </button>
#                                 </h6>
#                                 {symptomLesions} 
                        
#                             </div>

#                             <div class="tab-pane fade list-group-item bg-body border-0" id="profile" role="tabpanel" aria-labelledby="profile-tab">
#                                 <h6 class="card-subtitle mb-2 text-muted">Lesion network maps for {symptom}:
#                                     &nbsp;&nbsp;
#                                     <button id='questionButton4' type="button" data-bs-placement="right" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Lesion network map matches:" 
#                                     data-bs-content="All lesion network maps associated with the select symptom ({symptom}) are listed here. 
#                                     <br><br> You may click on the author's name to be redirected to a new page that contains more detailed information on the specific case in question.
#                                     <br><br>To load results as overlays on the viewer, toggle the respective view icons to the right.">
#                                         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                             <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                             <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                         </svg>
#                                     </button>
#                                 </h6>
#                                 {symptomNetworks}
#                             </div>
#                         </div>
#                     </div>
#                 </div>
#                 {javascript}
#                 {chart}
#             </div>
#         </div>
#         <br>
#     </div>
    
#     """
#     return htmlString
# def page(request):
#     query = """SELECT distinct CONCAT('<option class="dropdown-item" value="', symptom, '">', ROW_NUMBER() OVER (ORDER BY symptom), ': ', Symptom, '</option>') AS symptom 
#             FROM (select distinct symptom from lesiontable
#                 ) as subqery
#             order by symptom"""
#     dropdownList = ""
#     column_names, rows = genericFunctions.execute_query(query)
#     for row in rows:
#         for value in row:
#             dropdownList += value
#     if request.GET:
#         symptom = request.GET.get('symptom')
#         dynamicContent = f"""<div class='container'>
                               
#                                     <form method='_GET'>
#                                                 <div class="input-group mb-3  input-group-lg">
#                                                     <select id='selectMenu'class='form-select' aria-label='Select an option' name='symptom'>
#                                                     {dropdownList} 
#                                                     </select> 
#                                                     <script>
#                                                         const symptom = "{symptom}" // get the value of the symptom variable
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
#         dynamicContent += getDynamicContent(symptom)
#     else:
#         query = """SELECT distinct symptom FROM lesiontable"""
#         dynamicContent = genericFunctions.query_to_table(query, "list")
#         dynamicContent += genericFunctions.getJavascript()
#         dynamicContent = f"""<div class='container'>
#                                 <div class="card">
#                                     <div class="card-header">
#                                         <br>
#                                         <h4 class="card-subtitle mb-2 text-muted"> Select a symptom to view lesion maps in our database:</h4>
#                                             <form method='_GET'>
#                                                 <div class="input-group mb-3  input-group-lg">
#                                                     <select class='form-select' aria-label='Select an option' name='symptom'>
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
#                                             <h3 class='card-subtitle mb-2 text-muted'>All Symptoms</h3>
#                                             {dynamicContent}
#                                         </div>
#                                     <!-- </div> -->                                   
#                                 </div>
#                             </div>
#                             <br><br><br><br><br><br><br>"""
#     html_string = genericFunctions.getHTMLString()
#     html_string = html_string.replace("%%REPLACE_ME%%", dynamicContent).replace("symptomsActive", "active").replace("%%REPLACE_PAGE_NAME%%", "Symptoms")
#     return HttpResponse(html_string)