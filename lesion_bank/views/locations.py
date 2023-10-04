from django.http import HttpResponse, HttpRequest
from . import genericFunctions

tracingsImages = []
networksImages = []

def location_view(request):
    from . import charts
    if not request.GET:
        extra_script = """
        <script>
            reloadViewer(["GenericMNI.nii",0]); 
        </script>"""
        dynamic_content = False
    else:
        extra_script = ""
        dynamic_content = True
    from django.shortcuts import render
    # Get important values from GET string
    def get_value_as_int(dictionary, key, default_value):
        try:
            return int(dictionary.get(key, default_value))
        except ValueError:
            return default_value
    x = get_value_as_int(request.GET, 'x', 0)
    y = get_value_as_int(request.GET, 'y', 0)
    z = get_value_as_int(request.GET, 'z', 0)
    dist = get_value_as_int(request.GET, 'dist', 1)
    location_id = get_value_as_int(request.GET, 'location_id', 0)

    if dist == 0:
        x += x % 2
        y += y % 2
        z += z % 2

    if location_id < 1:
        query_string = """
            SELECT anatomical_name, atlaskey.locationid
            FROM atlastable
            LEFT JOIN atlaskey
            ON atlastable.atlasid = atlaskey.atlas_id
            AND atlastable.locationid = atlaskey.locationid
            WHERE x = %(x)s
            AND y = %(y)s 
            AND z = %(z)s
        """
        params = {
            'x': x,
            'y': y,
            'z': z
        }

        row = genericFunctions.fetch_single_row(query_string, params)

        if row:
            anatomicalName = row["anatomical_name"]
            location_id_from_voxel = row["locationid"]
        else:
            anatomicalName = "Unknown"
            location_id_from_voxel = "0"
        initial_coord = [x,y,z]
        anatomicalNameHTML = anatomicalName
        regionOfInterest = str(x) + ', ' + str(y) + ', ' + str(z) 
        if dynamic_content:
            tracingsquery = """
            select coordinate, lesion_info as "Lesion Info", symptom, tracing_file_name, network_file_name FROM (
                select dist, coordinate, lesion_info, symptom, tracing_file_name, network_file_name, x, y , z from (
                    SELECT DISTINCT ON (tracing_file_name)
                        SUM(ABS(tracingscoordinates.x-(%(x)s)) + ABS(tracingscoordinates.Y-(%(y)s)) + ABS(tracingscoordinates.Z-(%(z)s))) as dist,
                        concat('<a href="../locations/?x=', tracingscoordinates.x,'&y=',tracingscoordinates.y,'&z=',tracingscoordinates.z,'"> ',tracingscoordinates.x,' ',tracingscoordinates.y,' ',tracingscoordinates.z,' </a>') as coordinate,
                        concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as lesion_info,
                        Symptom,
                        Tracing_File_Name,
                        Network_File_Name
                        ,x,y,z
                    FROM TracingsCoordinates 
                    LEFT JOIN LesionTable ON LesionTable.Lesion_ID = TracingsCoordinates.Lesion_ID 
                    WHERE abs(tracingscoordinates.x - (%(x)s)) <= %(dist)s AND abs(tracingscoordinates.y - (%(y)s)) <= %(dist)s AND abs(tracingscoordinates.z - (%(z)s)) <= %(dist)s
                    GROUP BY tracingscoordinates.x, tracingscoordinates.y, tracingscoordinates.z, author, symptom, tracing_file_name, network_file_name, LesionTable.lesion_id
                    ORDER BY tracing_file_name, dist) as inner1
                    order by dist) as inner2
                    left join 
                    atlastable on atlastable.x = inner2.x
                    and atlastable.y = inner2.y
                    and atlastable.z = inner2.z
                    left join atlaskey 
                    on atlaskey.locationid = atlastable.locationid and atlaskey.atlas_id = atlastable.atlasid
                """
            tracingsparams = {"x": x, "y": y, "z": z, "dist": dist}

            networksquery = """
            select coordinate, t_stat, lesion_info as "Lesion Info", symptom, tracing_file_name, network_file_name from (
                select distinct on (tracing_file_name) * from (
                    SELECT 
                        SUM(ABS(X-(%(x)s)) + ABS(Y-(%(y)s)) + ABS(Z-(%(z)s))) as dist, concat('<a href="../locations/?x=', x,'&y=',y,'&z=',z,'"> ',x,' ',y,' ',z,' </a>') as Coordinate
                        , t_stat
                        , concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as lesion_info
                        , symptom
                        , tracing_file_name
                        , network_file_name 
                    FROM NetworksCoordinates
                    LEFT JOIN LesionTable 
                    ON 
                        LesionTable.Lesion_ID = NetworksCoordinates.Lesion_ID
                    WHERE 
                        x >= %(x_minus_dist)s and x <= %(x_plus_dist)s
                        and y >= %(y_minus_dist)s and y <= %(y_plus_dist)s
                        and z >= %(z_minus_dist)s and z <= %(z_plus_dist)s
                    group by coordinate, t_stat, networkscoordinates.lesion_id, LesionTable.author, LesionTable.symptom, LesionTable.tracing_file_name, LesionTable.network_file_name, LesionTable.Lesion_ID
                    order by tracing_file_name, t_stat desc
                ) as inner1) 
            as inner2 order by t_stat desc
            LIMIT 30
            """
            networksparams = {"x": x, "y": y, "z": z, "x_minus_dist": x - dist, "x_plus_dist": x + dist, "y_minus_dist": y - dist, "y_plus_dist": y + dist, "z_minus_dist": z - dist, "z_plus_dist": z + dist}

            average_tstat_query = """
            select 
                avg(t_stat) as avg
                , symptom 
            from networkscoordinates 
            left join lesiontable
                on lesiontable.lesion_id = networkscoordinates.lesion_id
            WHERE 
                x >= %(x_minus_dist)s and x <= %(x_plus_dist)s
                and y >= %(y_minus_dist)s and y <= %(y_plus_dist)s
                and z >= %(z_minus_dist)s and z <= %(z_plus_dist)s
            group by symptom
            order by avg desc
            """
            average_tstatparams = {"x_minus_dist": x - dist, "x_plus_dist": x + dist, "y_minus_dist": y - dist, "y_plus_dist": y + dist, "z_minus_dist": z - dist, "z_plus_dist": z + dist}


    else:
        query = "SELECT anatomical_name FROM atlaskey WHERE locationid = %(locationid)s and atlas_id = 0"
        params = {'locationid': location_id}
        anatomicalName = genericFunctions.fetch_single_row(query, params)["anatomical_name"]
        anatomicalNameHTML = ""
        regionOfInterest = anatomicalName
        location_id_from_voxel = 0
        query_params = {'location_id': location_id}
        initialCoordQuery = """
                        select 
                            concat(mode_x, ', ', mode_y, ', ', mode_z) as coordinate
                        from (
                            SELECT
                                (SELECT x FROM atlastable WHERE locationid = %(location_id)s GROUP BY x ORDER BY COUNT(*) DESC LIMIT 1) AS mode_x
                                , (SELECT y FROM atlastable WHERE locationid = %(location_id)s GROUP BY y ORDER BY COUNT(*) DESC LIMIT 1) AS mode_y
                                , (SELECT z FROM atlastable WHERE locationid = %(location_id)s GROUP BY z ORDER BY COUNT(*) DESC LIMIT 1) AS mode_z     
                            ) as innerquery
                    """
        initial_coord = genericFunctions.fetch_single_row(initialCoordQuery, query_params)["coordinate"].split(",")
        if dynamic_content:
            tracingsquery = """
            select 
                concat('<a href="../locations/?x=', innerquery.x,'&y=',innerquery.y,'&z=',innerquery.z,'"> ',innerquery.x,' ',innerquery.y,' ',innerquery.z,' </a>') as coordinate
                ,concat('<a href="../cases/?id=', innerquery.Lesion_ID, '">', author, '</a>') as "Lesion Info"
                , symptom
                , tracing_file_name
                , network_file_name
            from   
                (SELECT DISTINCT ON (tracingscoordinates.lesion_id1) *
                FROM lesiontable
                LEFT join (select x, y, z, lesion_id as lesion_id1 from tracingscoordinates) as tracingscoordinates ON lesiontable.lesion_id = tracingscoordinates.lesion_id1
                LEFT JOIN 
                    (select x as x1, y as y1, z as z1, atlasid, locationid from atlastable) as atlastable
                    ON tracingscoordinates.x = atlastable.x1
                    AND tracingscoordinates.y = atlastable.y1
                    AND tracingscoordinates.z = atlastable.z1
                left join atlaskey on atlaskey.locationid = atlastable.locationid
                WHERE atlastable.locationid = %(location_id)s
                ORDER BY tracingscoordinates.lesion_id1, tracingscoordinates.lesion_id1) as innerquery
            """
            tracingsparams = {"location_id": location_id}

            networksquery = """
            select 
                concat('<a href="../locations/?x=', innerquery.x,'&y=',innerquery.y,'&z=',innerquery.z,'"> ',innerquery.x,' ',innerquery.y,' ',innerquery.z,' </a>') as coordinate
                ,t_stat
                ,concat('<a href="../cases/?id=', innerquery.Lesion_ID, '">', author, '</a>') as "Lesion Info"
                , symptom
                , tracing_file_name
                , network_file_name
            from (
                SELECT DISTINCT ON (networkscoordinates.lesion_id1) *
                    FROM lesiontable
                    LEFT join (select x, y, z, lesion_id as lesion_id1, t_stat from networkscoordinates) as networkscoordinates ON lesiontable.lesion_id = networkscoordinates.lesion_id1
                    LEFT JOIN 
                        (select x as x1, y as y1, z as z1, atlasid, locationid from atlastable) as atlastable
                        ON networkscoordinates.x = atlastable.x1
                        AND networkscoordinates.y = atlastable.y1
                        AND networkscoordinates.z = atlastable.z1
                    left join atlaskey on atlaskey.locationid = atlastable.locationid
                    WHERE atlastable.locationid = %(location_id)s
                    and networkscoordinates.t_stat > 90
                    ORDER BY networkscoordinates.lesion_id1, networkscoordinates.t_stat desc
                    ) as innerquery
            order by innerquery.t_stat desc
            limit 30     
            """
            networksparams = {"location_id": location_id}

            average_tstat_query = """
            select 
                avg_tstat as avg
                , symptom
                , locationid
            from 
                avg_t_stat_location
            where 
                locationid = %(location_id)s
            """
            average_tstatparams = {"location_id": location_id}

    if dynamic_content:
        returnedTracings = genericFunctions.query_to_table_improved(tracingsquery, tracingsparams, "tracing", True, False, True)       
        returnedNetworksPos = genericFunctions.query_to_table_improved(networksquery, networksparams, "network", True, False)
        returnedNetworksNeg = genericFunctions.query_to_table_improved(networksquery.replace("desc", "asc").replace("and networkscoordinates.t_stat > 90", "and networkscoordinates.t_stat < -50"), networksparams, "network", True, True)
        t_stat_chart = charts.queryToChart_improved(average_tstat_query,average_tstatparams, "Average T_Stat Value", "symptom")
    
    else:
        returnedTracings = ""   
        returnedNetworksPos = ""
        returnedNetworksNeg = ""
        t_stat_chart = ""

    ## Get list of options for the search bar:
    query = f"""
        SELECT 
            opt
        FROM
            (SELECT DISTINCT
                CASE WHEN locationid = '{int(location_id)}' THEN 
                    CONCAT('<option selected value="', locationid, '">', anatomical_name, '</option>')
                WHEN locationid = '{int(location_id_from_voxel)}' THEN 
                    CONCAT('<option selected value="', locationid, '">', anatomical_name, '</option>')
                ELSE
                    CONCAT('<option value="', locationid, '">', anatomical_name, '</option>')
                END AS opt,
                anatomical_name
            FROM 
                atlaskey
            ORDER BY anatomical_name) AS innerquery;
    """
    location_options_string = genericFunctions.fetch_all_rows(query)
    content_string = f""""""

    return render(request, 'lesion_bank/locations.html',{'title': 'Locations',
                                                        'dynamic_content':dynamic_content,
                                                        'x': x,
                                                        'y': y,
                                                        'z': z,
                                                        'dist': dist,
                                                        'location_id': location_id,
                                                        'location_id_from_voxel': location_id_from_voxel,
                                                        'location_options_string': location_options_string,
                                                        'anatomicalNameHTML': anatomicalNameHTML,
                                                        'regionOfInterest': regionOfInterest,
                                                        'initial_coord': initial_coord,
                                                        'initial_coord_1': initial_coord[0],
                                                        'initial_coord_2': initial_coord[1],
                                                        'initial_coord_3': initial_coord[2],
                                                        'returnedTracings': returnedTracings,
                                                        'returnedNetworksPos': returnedNetworksPos,
                                                        'returnedNetworksNeg':returnedNetworksNeg,
                                                        't_stat_chart':t_stat_chart,
                                                        'extra_content' : content_string,
                                                        'extra_script': extra_script
                                                        })


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

# def locations_view(request):
#     import requests
#     global tracingsImages
#     global networksImages 
#     tracingsImages = []
#     networksImages = []

#     if request.GET:
#         from . import charts
#         x = int(request.GET.get('x', '0'))
#         y = int(request.GET.get('y', '0'))
#         z = int(request.GET.get('z', '0'))
#         if 'location_id' in request.GET:
#             location_id = int(request.GET.get('location_id'))
#         else: 
#             location_id = 0
#         if 'dist' in request.GET:
#                 dist = int(request.GET.get('dist'))
#         else:
#             dist = 1
#         if dist == 0:
#             if (x % 2 == 1) or (x % 2 == -1):
#                 x += 1
#             if (y % 2 == 1) or (y % 2 == -1):
#                 y += 1
#             if (z % 2 == 1) or (z % 2 == -1):
#                 z += 1
#         # tracingsquery = f"""
#         # select coordinate, lesion_info as "Lesion Info", symptom, tracing_file_name, network_file_name FROM (
#         # select dist, coordinate, lesion_info, symptom, tracing_file_name, network_file_name from (
#         #     SELECT DISTINCT ON (tracing_file_name)
#         #         SUM(ABS(tracingscoordinates.x-({x})) + ABS(tracingscoordinates.Y-({y})) + ABS(tracingscoordinates.Z-({z}))) as dist,
#         #         concat('<a href="../locations/?x=', tracingscoordinates.x,'&y=',tracingscoordinates.y,'&z=',tracingscoordinates.z,'"> ',tracingscoordinates.x,' ',tracingscoordinates.y,' ',tracingscoordinates.z,' </a>') as coordinate,
#         #         concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as lesion_info,
#         #         Symptom,
#         #         Tracing_File_Name,
#         #         Network_File_Name
#         #     FROM TracingsCoordinates 
#         #     LEFT JOIN LesionTable ON LesionTable.Lesion_ID = TracingsCoordinates.Lesion_ID 
#         #     WHERE abs(tracingscoordinates.x - ({x})) <= {dist} AND abs(tracingscoordinates.y - ({y})) <= {dist} AND abs(tracingscoordinates.z - ({z})) <= {dist}
#         #     GROUP BY tracingscoordinates.x, tracingscoordinates.y, tracingscoordinates.z, author, symptom, tracing_file_name, network_file_name, LesionTable.lesion_id
#         #     ORDER BY tracing_file_name, dist) as inner1
#         #     order by dist) as inner2
#         # """
#         if location_id != 0:
#             initialCoordQuery = f"""
#                 select 
#                     concat(mode_x, ', ', mode_y, ', ', mode_z) as coordinate
#                 from (
#                     SELECT
#                         (SELECT x FROM atlastable WHERE locationid = {location_id} GROUP BY x ORDER BY COUNT(*) DESC LIMIT 1) AS mode_x
#                         , (SELECT y FROM atlastable WHERE locationid = {location_id} GROUP BY y ORDER BY COUNT(*) DESC LIMIT 1) AS mode_y
#                         , (SELECT z FROM atlastable WHERE locationid = {location_id} GROUP BY z ORDER BY COUNT(*) DESC LIMIT 1) AS mode_z     
#                     ) as innerquery
#             """
#             initialCoord = genericFunctions.fetch_single_row(initialCoordQuery)["coordinate"].split(",")
#             tracingsquery = f"""
#             select 
#                 concat('<a href="../locations/?x=', innerquery.x,'&y=',innerquery.y,'&z=',innerquery.z,'"> ',innerquery.x,' ',innerquery.y,' ',innerquery.z,' </a>') as coordinate
#                 ,concat('<a href="../cases/?id=', innerquery.Lesion_ID, '">', author, '</a>') as "Lesion Info"
#                 , symptom
#                 , tracing_file_name
#                 , network_file_name
#             from   
#                 (SELECT DISTINCT ON (tracingscoordinates.lesion_id1) *
#                 FROM lesiontable
#                 LEFT join (select x, y, z, lesion_id as lesion_id1 from tracingscoordinates) as tracingscoordinates ON lesiontable.lesion_id = tracingscoordinates.lesion_id1
#                 LEFT JOIN 
#                     (select x as x1, y as y1, z as z1, atlasid, locationid from atlastable) as atlastable
#                     ON tracingscoordinates.x = atlastable.x1
#                     AND tracingscoordinates.y = atlastable.y1
#                     AND tracingscoordinates.z = atlastable.z1
#                 left join atlaskey on atlaskey.locationid = atlastable.locationid
#                 WHERE atlastable.locationid = {location_id}
#                 ORDER BY tracingscoordinates.lesion_id1, tracingscoordinates.lesion_id1) as innerquery
#             """
#             networksquery = f"""
#             select 
#                 concat('<a href="../locations/?x=', innerquery.x,'&y=',innerquery.y,'&z=',innerquery.z,'"> ',innerquery.x,' ',innerquery.y,' ',innerquery.z,' </a>') as coordinate
#                 ,t_stat
#                 ,concat('<a href="../cases/?id=', innerquery.Lesion_ID, '">', author, '</a>') as "Lesion Info"
#                 , symptom
#                 , tracing_file_name
#                 , network_file_name
#             from (
#                 SELECT DISTINCT ON (networkscoordinates.lesion_id1) *
#                     FROM lesiontable
#                     LEFT join (select x, y, z, lesion_id as lesion_id1, t_stat from networkscoordinates) as networkscoordinates ON lesiontable.lesion_id = networkscoordinates.lesion_id1
#                     LEFT JOIN 
#                         (select x as x1, y as y1, z as z1, atlasid, locationid from atlastable) as atlastable
#                         ON networkscoordinates.x = atlastable.x1
#                         AND networkscoordinates.y = atlastable.y1
#                         AND networkscoordinates.z = atlastable.z1
#                     left join atlaskey on atlaskey.locationid = atlastable.locationid
#                     WHERE atlastable.locationid = {location_id}
#                     and networkscoordinates.t_stat > 90
#                     ORDER BY networkscoordinates.lesion_id1, networkscoordinates.t_stat desc
#                     ) as innerquery
#             order by innerquery.t_stat desc
#             limit 30     
#             """
#             # average_tstat_query = f"""
#             # select 
#             #     avg(t_stat) as avg
#             #     , symptom
#             #     , anatomical_name
#             # from networkscoordinates 
#             # left join atlastable
#             #     on networkscoordinates.x = atlastable.x
#             #     and networkscoordinates.y = atlastable.y 
#             #     and networkscoordinates.z = atlastable.z 
#             # left join lesiontable 
#             #     on lesiontable.lesion_id = networkscoordinates.lesion_id
#             # left join atlaskey 
#             #     on atlaskey.locationid = atlastable.locationid
#             # where 
#             #     atlastable.locationid = {location_id}
#             # group by 
#             #     symptom
#             #     , anatomical_name
#             # order by avg desc
#             # """
#             average_tstat_query = f"""
#             select 
#                 avg_tstat as avg
#                 , symptom
#                 , locationid
#             from 
#                 avg_t_stat_location
#             where 
#                 locationid = {location_id}
#             """
#         else:
#             initialCoord = [x,y,z]
#             tracingsquery = f"""select coordinate, lesion_info as "Lesion Info", symptom, tracing_file_name, network_file_name FROM (
#             select dist, coordinate, lesion_info, symptom, tracing_file_name, network_file_name, x, y , z from (
#                 SELECT DISTINCT ON (tracing_file_name)
#                     SUM(ABS(tracingscoordinates.x-({x})) + ABS(tracingscoordinates.Y-({y})) + ABS(tracingscoordinates.Z-({z}))) as dist,
#                     concat('<a href="../locations/?x=', tracingscoordinates.x,'&y=',tracingscoordinates.y,'&z=',tracingscoordinates.z,'"> ',tracingscoordinates.x,' ',tracingscoordinates.y,' ',tracingscoordinates.z,' </a>') as coordinate,
#                     concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as lesion_info,
#                     Symptom,
#                     Tracing_File_Name,
#                     Network_File_Name
#                     ,x,y,z
#                 FROM TracingsCoordinates 
#                 LEFT JOIN LesionTable ON LesionTable.Lesion_ID = TracingsCoordinates.Lesion_ID 
#                 WHERE abs(tracingscoordinates.x - ({x})) <= {dist} AND abs(tracingscoordinates.y - ({y})) <= {dist} AND abs(tracingscoordinates.z - ({z})) <= {dist}
#                 GROUP BY tracingscoordinates.x, tracingscoordinates.y, tracingscoordinates.z, author, symptom, tracing_file_name, network_file_name, LesionTable.lesion_id
#                 ORDER BY tracing_file_name, dist) as inner1
#                 order by dist) as inner2
#                 left join 
#                 atlastable on atlastable.x = inner2.x
#                 and atlastable.y = inner2.y
#                 and atlastable.z = inner2.z
#                 left join atlaskey 
#                 on atlaskey.locationid = atlastable.locationid and atlaskey.atlas_id = atlastable.atlasid
#             """
#             networksquery = f"""
#             select coordinate, t_stat, lesion_info as "Lesion Info", symptom, tracing_file_name, network_file_name from (
#                 select distinct on (tracing_file_name) * from (
#                     SELECT 
#                         SUM(ABS(X-({x})) + ABS(Y-({y})) + ABS(Z-({z}))) as dist, concat('<a href="../locations/?x=', x,'&y=',y,'&z=',z,'"> ',x,' ',y,' ',z,' </a>') as Coordinate
#                         , t_stat
#                         , concat('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') as lesion_info
#                         , symptom
#                         , tracing_file_name
#                         , network_file_name 
#                     FROM NetworksCoordinates
#                     LEFT JOIN LesionTable 
#                     ON 
#                         LesionTable.Lesion_ID = NetworksCoordinates.Lesion_ID
#                     WHERE 
#                         x >= {x-dist} and x <= {x+dist}
#                         and y >= {y-dist} and y <= {y+dist}
#                         and z >= {z-dist} and z <= {z+dist}
#                     group by coordinate, t_stat, networkscoordinates.lesion_id, LesionTable.author, LesionTable.symptom, LesionTable.tracing_file_name, LesionTable.network_file_name, LesionTable.Lesion_ID
#                     order by tracing_file_name, t_stat desc
#                 ) as inner1) 
#             as inner2 order by t_stat desc
#             LIMIT 30
#             """
#             average_tstat_query = f"""
#             select 
#                 avg(t_stat) as avg
#                 , symptom 
#             from networkscoordinates 
#             left join lesiontable
#                 on lesiontable.lesion_id = networkscoordinates.lesion_id
#             WHERE 
#                 x >= {x-dist} and x <= {x+dist}
#                 and y >= {y-dist} and y <= {y+dist}
#                 and z >= {z-dist} and z <= {z+dist}
#             group by symptom
#             order by avg desc
#             """

#         returnedTracings = genericFunctions.query_to_table(tracingsquery, "tracing", True, False, True)       
#         returnedNetworksPos = genericFunctions.query_to_table(networksquery, "network", True, False)
#         returnedNetworksNeg = genericFunctions.query_to_table(networksquery.replace("desc", "asc").replace("and networkscoordinates.t_stat > 90", "and networkscoordinates.t_stat < -50"), "network", True, True)
#         t_stat_chart = charts.queryToChart(average_tstat_query, "Average T_Stat Value", "symptom")
#         if location_id < 1:
#             base_url = "https://lesionbank.org/api/?type=atlas&"
#             response = requests.get(f"{base_url}x={x}&y={y}&z={z}")
#             try:
#                 anatomicalName = response.json()[0]["anatomical_name"]
#                 location_id_from_voxel = response.json()[0]["locationid"]
#             except (IndexError, KeyError, ValueError):
#                 # Handle the error here
#                 anatomicalName = "Unknown"  # Set a default value or take appropriate action
#                 location_id_from_voxel = "0"
#             anatomicalNameHTML = anatomicalName
            
#             regionOfInterest = str(x) + ', ' + str(y) + ', ' + str(z) 
#         else:
#             query = f"SELECT anatomical_name FROM atlaskey WHERE locationid = {location_id} and atlas_id = 0"
#             anatomicalName = genericFunctions.fetch_single_row(query)["anatomical_name"]
#             anatomicalNameHTML = ""
#             regionOfInterest = anatomicalName
#             location_id_from_voxel = 0

#         HTMLcontainer = f"""
            
#                 <div class="card card-body">
#                     <div class="row">
#                          <div id='papayaHolder' class='papayaHolder col-sm-6'>
#                             <div class='papaya' id='papaya1' data-params='params'></div>
                            
#                             <div style='padding: 10px;' class='input-group mb-3' id='selectedCoordinate'>
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
#                         </div> 
#                         <div class='col-sm-6'>
#                             <div class='card'>
#                                 <div class="card-header">
#                                     <h3 class='card-title'><button id='questionButton2' type="button" data-bs-placement="left" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Results:" data-bs-content="This display contains an ordered list of results from our lesion dataset that match the search parameters.<br><br>Case studies with lesions near the target coordinate are shown first (if there are any).<br><br>Next are shown lesion network maps that are correlated with the target coordinate;<br><br>Lastly, lesion network maps that are anticorrelated at the target coordinate are listed.<br><br>Note that our lesion dataset is based on 2mm coordinates; thus exact matches on odd-numbered coordinate searches are currently not possible. For best results, we recommend a minimum distance of 1 mm.">
#                                         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                             <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                             <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                         </svg>
#                                     </button> Results for {regionOfInterest}:</h3> 
#                                     <h6>{anatomicalNameHTML}</h6>
                                    
#                                 </div>
#                                 <ul class="nav nav-tabs bg-body" id="myTab" role="tablist">
#                                     <li class="nav-item bg-body border-bottom-0" role="presentation">
#                                         <button class="nav-link active " id="home-tab" data-bs-toggle="tab" data-bs-target="#home" type="button" role="tab" aria-controls="home" aria-selected="true">Lesion Case Reports</button>
#                                     </li>
#                                     <li class="nav-item bg-body" role="presentation">
#                                         <button class="nav-link" id="profile-tab" data-bs-toggle="tab" data-bs-target="#profile" type="button" role="tab" aria-controls="profile" aria-selected="false">Positive Networks</button>
#                                     </li>
#                                     <li class="nav-item bg-body" role="presentation">
#                                         <button class="nav-link" id="contact-tab" data-bs-toggle="tab" data-bs-target="#contact" type="button" role="tab" aria-controls="contact" aria-selected="false">Negative Networks</button>
#                                     </li>
#                                 </ul>

#                                 <div class="tab-content list-group list-group-flush " id="myTabContent">
#                                     <div class="list-group-item border-0 bg-body border-danger" style='display:none; --bs-list-group-active-border-color: unset !important;' ></div>
#                                     <div class=" tab-pane fade show active list-group-item bg-body" id="home" role="tabpanel" aria-labelledby="home-tab">
                                
#                                         <h6 class="card-subtitle mb-2 text-muted"> Lesions within {dist} mm of {regionOfInterest}:
#                                             &nbsp;&nbsp;
#                                             <button id='questionButton3' type="button" data-bs-placement="right" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Lesion matches:" data-bs-content="Any lesions found within the search parameters are listed here, ordered by increasing distance from the target coordinate. <br><br> You may click on the author's name to be redirected to a new page that contains more detailed information on the specific case in question. You may also click on the symptom name to search our dataset for all lesions and network maps involving the specified symptom.<br><br>To load results as overlays on the viewer, toggle the view icons to the right.">
#                                                                                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                                                                     <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                                                                     <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                                                                 </svg>
#                                             </button>
#                                         </h6>
#                                         {returnedTracings} 
                                
#                                     </div>

#                                     <div class="tab-pane fade list-group-item bg-body border-0" id="profile" role="tabpanel" aria-labelledby="profile-tab">
#                                         <h6 class="card-subtitle mb-2 text-muted"> Top positively correlated lesion network maps near {regionOfInterest}:
#                                             &nbsp;&nbsp;
#                                             <button id='questionButton4' type="button" data-bs-placement="right" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Positive lesion network map matches:" data-bs-content="The top lesion network maps with positive functional connectivity to coordinates within the search parameters are listed, ordered by decreasing t statistic. The t statistic represents the degree of functional connectivity between the lesion and the coordinate. Higher positive t_statistics indicate higher positive functional connectivity. <br><br> You may click on the author's name to be redirected to a new page that contains more detailed information on the specific case in question. You may also click on the symptom name to search our dataset for all lesions and network maps involving the specified symptom. <br><br>To load results as overlays on the viewer, toggle the respective view icons to the right.">
#                                                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                                     <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                                     <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                                 </svg>
#                                             </button>
#                                         </h6>
#                                         {returnedNetworksPos}
#                                         <div>
#                                         {t_stat_chart}
#                                         </div>
#                                     </div>

#                                     <div class="tab-pane fade list-group-item bg-body border-0" id="contact" role="tabpanel" aria-labelledby="contact-tab">
#                                         <h6 class="card-subtitle mb-2 text-muted"> Top negatively correlated lesion network maps near {regionOfInterest}:
#                                             &nbsp;&nbsp;
#                                             <button id='questionButton4' type="button" data-bs-placement="right" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-html="true" data-bs-title="Negative lesion network map matches:" data-bs-content="The top lesion network maps with negative functional connectivity to coordinates within the search parameters are listed, ordered by increasing t statistic. The t statistic represents the degree of functional connectivity between the lesion and the coordinate. More negative t_statistics indicate stronger anticorrelated functional connectivity. <br><br> You may click on the author's name to be redirected to a new page that contains more detailed information on the specific case in question. You may also click on the symptom name to search our dataset for all lesions and network maps involving the specified symptom. <br><br>To load results as overlays on the viewer, toggle the view icons to the right.">
#                                                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                                     <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                                     <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                                 </svg>
#                                             </button>
#                                         </h6>
#                                         {returnedNetworksNeg}
#                                         <div>
#                                         {t_stat_chart}
#                                         </div>
#                                     </div>

#                                 </div>

                               
#                             </div>
#                         </div>
#                     </div>
#                 </div>
#         """
#         outputStr = pageStyles + getSearchBar(x,y,z, dist, location_id, location_id_from_voxel) + HTMLcontainer + "<br><br></div>" + genericFunctions.getJavascript(initialCoord[0], initialCoord[1], initialCoord[2]) 
#     else:
#         outputStr = pageStyles + getSearchBar('','','', 1) + "</div>"
#         outputStr += f"""
#         <div class='container'>
#             <div class="card card-body">
#                     <div class="row">
#                          <div id='papayaHolder' class='papayaHolder col-sm-6'>
#                             <div class='papaya' id='papaya1' data-params='params'></div>
#                             <div style='padding: 10px;' class='input-group mb-3' id='selectedCoordinate'>
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
#                         </div> 
#                     </div>
#             </div>
#         </div>
#         """ + genericFunctions.getJavascript() + """
#         <script>
#             reloadViewer(["GenericMNI.nii",0]); 
#         </script>"""
    
#     html_string = genericFunctions.getHTMLString()
#     html_string = html_string.replace("%%REPLACE_ME%%", outputStr).replace("locationsActive", "active").replace("%%REPLACE_PAGE_NAME%%", "Locations")
#     return HttpResponse(html_string)


# def getSearchBar(x=0,y=0,z=0, dist=1, location_id=0, location_id_from_voxel=0):
#     html = f"""
#         <div class='container'>
#             <ul class="nav nav-tabs bg-body" id="myTab" role="tablist">
#                 <li class="nav-item" role="presentation">
#                     <a class="nav-link active" id="coordinate-tab" data-bs-toggle="tab" href="#coordinateSearchBar" role="tab" aria-controls="coordinateSearchBar" aria-selected="true">Coordinate Search</a>
#                 </li>
#                 <li class="nav-item" role="presentation">
#                     <a class="nav-link" id="location-tab" data-bs-toggle="tab" href="#locationSearchBar" role="tab" aria-controls="locationSearchBar" aria-selected="false">Anatomy Search</a>
#                 </li>
#             </ul>

#             <div class="tab-content" >
#                 <div class="tab-pane fade show active" id="coordinateSearchBar" role="tabpanel" aria-labelledby="coordinate-tab">
#                     <form method='GET'>
#                     <div class="input-group mb-3 input-group-lg" style='padding:none !important; margin-bottom:none !important;'>
#                         <!-- Lots of content for coordinate search -->
#                         <div class="input-group input-group-lg">
#                             <button id='questionButton0' type="button" data-bs-placement="bottom" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-title="Coordinate Search:" data-bs-content="Choose a coordinate (MNI Space) and a distance radius to search our lesion dataset for results near the specified coordinate. You may also search using the coordinate navigator below the image visualizer.">
#                                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                     <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                     <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                                 </svg>
#                             </button>
#                             <span disabled class="input-group-text bg-secondary bg-gradient ">Coordinate Search: </span>
#                             <span class="input-group-text">X</span>
#                             <input required type="number" class="form-control" placeholder="X" aria-label="X" name='x' id='x'  value='{x}'>
#                             <span class="input-group-text">Y</span>
#                             <input required type="number" class="form-control" placeholder="Y" aria-label="Y" name='y' id='y'  value='{y}'>
#                             <span class="input-group-text">Z</span>
#                             <input required type="number" class="form-control" placeholder="Z" aria-label="Z" name='z' id='z' value='{z}'>
#                             <span class="input-group-text">Within:</span>
#                             <select class="form-control" name='dist' id='dist'>"""
#     for i in range(7):
#         if i == dist:
#             html += f"""
#             <option selected value='{i}'>
#                 {i} mm
#             </option>
#             """
#         else:
#             html += f"""
#             <option value='{i}'>
#                 {i} mm
#             </option>
#             """
#     html += f"""
#                             </select>
#                             <button class="btn btn-outline-secondary" type="submit" id="button-addon1">Search</button>
#                         </div>        
#                     </div>
#                     </form>
#                 </div>
#                 <div class="tab-pane fade " id="locationSearchBar" role="tabpanel" aria-labelledby="location-tab">
#                     <form method='GET'>
#                     <div class="input-group mb-3 input-group-lg">
#                         <!-- Lots of content for location search -->
#                         <button id='questionButton0' type="button" data-bs-placement="bottom" class="btn btn-sm btn-primary bg-gradient" data-bs-toggle="popover" data-bs-title="Anatomy Search:" data-bs-content="Choose an anatomical location to search our lesion dataset for results within the region. You may also search using the coordinate navigator below the image visualizer.">
#                             <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
#                                 <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
#                                 <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
#                             </svg>
#                         </button>
#                         <span disabled class="input-group-text bg-secondary bg-gradient ">Anatomy Search:</span>
#                         <select class="form-control" name='location_id' id='location_id'>"""
#     query = f"""
#         SELECT 
#             opt
#         FROM
#             (SELECT DISTINCT
#                 CASE WHEN locationid = '{location_id}' THEN 
#                     CONCAT('<option selected value="', locationid, '">', anatomical_name, '</option>')
#                 WHEN locationid = '{location_id_from_voxel}' THEN 
#                     CONCAT('<option selected value="', locationid, '">', anatomical_name, '</option>')
#                 ELSE
#                     CONCAT('<option value="', locationid, '">', anatomical_name, '</option>')
#                 END AS opt,
#                 anatomical_name
#             FROM 
#                 atlaskey
#             ORDER BY anatomical_name) AS innerquery;
#     """
#     location_options_string = genericFunctions.fetch_all_rows(query)
#     html += location_options_string

#     html += f"""
#                         </select>
#                         <button class="btn btn-outline-secondary" type="submit" id="button-addon2">Search</button>
#                     </div>
#                 </div>
#                 </form>
#             </div> 
#             <script>
#                 const location_id = {location_id} """ + """
#                 if (location_id > 0) {
#                     // Get the reference to the HTML element
#                     const element = document.getElementById('location-tab');

#                     // Programmatically trigger a click event on the element
#                     element.click();
#                     }
#             </script>
#     """
#     return html