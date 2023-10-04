# Import necessary modules
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connection

# Define view function that handles GET requests
@require_http_methods(["GET"])
def my_api_view(request):
    # Extract the GET parameters
    x_str = request.GET.get('x')
    y_str = request.GET.get('y')
    z_str = request.GET.get('z')
    lesion_id_str = request.GET.get('lesion_id')

    x = int(x_str) if x_str is not None else None
    y = int(y_str) if y_str is not None else None
    z = int(z_str) if z_str is not None else None
    lesion_id = int(lesion_id_str) if lesion_id_str is not None else None

    # Set default value to '1' if 'dist' parameter is not present
    dist = int(request.GET.get('dist', '1'))
    symptom = request.GET.get('symptom')
    
    type = request.GET.get('type')

    if type == "case_report":
        # Check if the required GET parameters are present
        if x is None or y is None or z is None:
            return JsonResponse({'error': 'Missing required parameters.'}, status=400)
        # Build the SQL query string
        query_string = f"""
            SELECT simple_coordinate as nearest_coordinate
            , anatomical_name
            , dist, inner2.lesion_id, author, symptom
                , CONCAT(
                        maxcoordtable.x
                        ,', '
                        ,maxcoordtable.y
                        ,', '
                        ,maxcoordtable.z
                    ) as peak_coordinate
                , CONCAT('https://lesionbank.org/static/MRIData/GZippedEverything/',tracing_file_name, '.gz') as tracing_file_name
                , CONCAT('https://lesionbank.org/static/MRIData/GZippedEverything/',network_file_name, '.gz') as network_file_name
                FROM (
                    SELECT dist, lesion_id, coordinate, simple_coordinate, author, lesion_info, symptom, tracing_file_name, network_file_name, x, y, z
                    FROM (
                        SELECT DISTINCT ON (tracing_file_name)
                            SUM(ABS(X-(%(x)s)) + ABS(Y-(%(y)s)) + ABS(Z-(%(z)s))) AS dist,
                            CONCAT('<a href="../locations/?x=', x, '&y=', y, '&z=', z, '"> ', x, ' ', y, ' ', z, ' </a>') AS coordinate
                            , CONCAT(
                                x
                                ,', '
                                ,y
                                ,', '
                                ,z                        
                            ) as simple_coordinate,
                            x, y, z,
                            LesionTable.Lesion_ID,
                            author,
                            CONCAT('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') AS lesion_info,
                            Symptom,
                            Tracing_File_Name,
                            Network_File_Name
                        FROM TracingsCoordinates 
                        LEFT JOIN LesionTable ON LesionTable.Lesion_ID = TracingsCoordinates.Lesion_ID 
                        WHERE ABS(x - (%(x)s)) <= %(dist)s AND ABS(y - (%(y)s)) <= %(dist)s AND ABS(z - (%(z)s)) <= %(dist)s
                        GROUP BY x, y, z, author, symptom, tracing_file_name, network_file_name, LesionTable.lesion_id
                        ORDER BY tracing_file_name, dist) AS inner1
                    ORDER BY dist) AS inner2
                LEFT JOIN 
                maxcoordtable 
                ON maxcoordtable.lesion_id = inner2.lesion_id
                left join atlastable
                on inner2.x = atlastable.x 
                and inner2.y = atlastable.y
                and inner2.z = atlastable.z
                and atlastable.atlasid = 0
                left join atlaskey 
                on atlaskey.locationid = atlastable.locationid
                and atlaskey.atlas_id = atlastable.atlasid
        """

        params = {
            'x': x,
            'y': y,
            'z': z,
            'dist': dist
        }
            
    elif type == "network_map":
        # Check if the required GET parameters are present
        if x is None or y is None or z is None:
            return JsonResponse({'error': 'Missing required parameters.'}, status=400)
        query_string = """
            SELECT coordinate as "peak_coordinate_within_search_parameters", inner2.t_stat, inner2.Lesion_Id, Author, symptom, CONCAT('https://lesionbank.org/static/MRIData/GZippedEverything/',tracing_file_name, '.gz') as tracing_file_name, CONCAT('https://lesionbank.org/static/MRIData/GZippedEverything/',network_file_name, '.gz') as network_file_name
             , CONCAT(
                    maxcoordtable.x
                    ,', '
                    ,maxcoordtable.y
                    ,', '
                    ,maxcoordtable.z
                ) as peak_coordinate
                , anatomical_name
            FROM (
                SELECT DISTINCT ON (tracing_file_name) *
                FROM (
                    SELECT
                        SUM(ABS(X-(%(x)s)) + ABS(Y-(%(y)s)) + ABS(Z-(%(z)s))) AS dist,
                        CONCAT(x, ', ', y, ', ', z) AS Coordinate,
                        t_stat,
                        LesionTable.Lesion_ID,
                        Author,
                        CONCAT('<a href="../cases/?id=', LesionTable.Lesion_ID, '">', author, '</a>') AS lesion_info,
                        Symptom,
                        Tracing_File_Name,
                        Network_File_Name
                    FROM NetworksCoordinates
                    LEFT JOIN LesionTable ON LesionTable.Lesion_ID = NetworksCoordinates.Lesion_ID
                    WHERE x >= (%(x_min)s) AND x <= (%(x_max)s)
                        AND y >= (%(y_min)s) AND y <= (%(y_max)s)
                        AND z >= (%(z_min)s) AND z <= (%(z_max)s)
                    GROUP BY coordinate, t_stat, networkscoordinates.lesion_id, LesionTable.author, LesionTable.symptom, LesionTable.tracing_file_name, LesionTable.network_file_name, LesionTable.Lesion_ID
                    ORDER BY tracing_file_name, t_stat DESC
                ) AS inner1
            ) AS inner2
            LEFT JOIN 
            maxcoordtable 
            ON maxcoordtable.lesion_id = inner2.lesion_id
            left join atlastable
            on maxcoordtable.x = atlastable.x and maxcoordtable.y = atlastable.y and maxcoordtable.z = atlastable.z and atlastable.atlasid = 0
            left join atlaskey on atlastable.locationid = atlaskey.locationID and atlastable.atlasid = atlaskey.atlas_id
            ORDER BY t_stat DESC
        """

        params = {
            'x_min': x - dist,
            'x_max': x + dist,
            'y_min': y - dist,
            'y_max': y + dist,
            'z_min': z - dist,
            'z_max': z + dist,
            'x': x,
            'y': y,
            'z': z
        }

    elif type == "symptom":
        # Check if the required GET parameters are present
        if symptom is None:
            return JsonResponse({'error': 'Missing required parameters.'}, status=400)
        query_string = """
            SELECT 
                lesiontable.lesion_id
                ,CONCAT(
                    maxcoordtable.x
                    , ', '
                    , maxcoordtable.y
                    , ', '
                    , maxcoordtable.z
                    ) AS peak_coordinate
                , COALESCE(anatomical_name, 'no data') as anatomical_name
                , author
                , symptom
                , CONCAT('https://lesionbank.org/static/MRIData/GZippedEverything/',tracing_file_name, '.gz') as tracing_file_name
                , CONCAT('https://lesionbank.org/static/MRIData/GZippedEverything/',network_file_name, '.gz') as network_file_name
            FROM LesionTable
            LEFT JOIN maxCoordtable ON maxcoordtable.lesion_id = lesiontable.lesion_id
            left join atlastable on atlastable.x = maxcoordtable.x and atlastable.y = maxcoordtable.y and atlastable.z = maxcoordtable.z and atlastable.atlasid = 0
            left join atlaskey on atlaskey.locationid = atlastable.locationid and atlaskey.atlas_id = atlastable.atlasid
            WHERE symptom ILIKE %s
        """
        params = ['%' + symptom + '%']
    
    elif type == "lesion_id":
        if lesion_id is None:
            return JsonResponse({'error': 'Missing required parameters.'}, status=400)
        query_string = """
            SELECT 
                lesiontable.lesion_id
                ,CONCAT(
                    maxcoordtable.x
                    , ', '
                    , maxcoordtable.y
                    , ', '
                    , maxcoordtable.z
                    ) AS peak_coordinate
                , anatomical_name
                , author
                , symptom
                , CONCAT('https://lesionbank.org/static/MRIData/GZippedEverything/',tracing_file_name, '.gz') as tracing_file_name
                , CONCAT('https://lesionbank.org/static/MRIData/GZippedEverything/',network_file_name, '.gz') as network_file_name
            FROM LesionTable
            LEFT JOIN maxCoordtable ON maxcoordtable.lesion_id = lesiontable.lesion_id
            left join atlastable on atlastable.x = maxcoordtable.x and atlastable.y = maxcoordtable.y and atlastable.z = maxcoordtable.z and atlastable.atlasid = 0
            left join atlaskey on atlaskey.locationid = atlastable.locationid and atlaskey.atlas_id = atlastable.atlasid
            WHERE lesiontable.lesion_id = %s
        """
        params = [lesion_id]
   
    elif type == "atlas":
        # Check if the required GET parameters are present
        if x is None or y is None or z is None:
            return JsonResponse({'error': 'Missing required parameters.'}, status=400)
        query_string = """
        select anatomical_name, atlaskey.locationid
        from atlastable
        left join atlaskey
        on atlastable.atlasid = atlaskey.atlas_id
        and atlastable.locationid = atlaskey.locationid
        where x = %(x)s
        and y = %(y)s 
        and z = %(z)s
        """
        params = {
            'x': x,
            'y': y,
            'z': z
        }

    else:
        return JsonResponse({'error': 'Missing required parameters.'}, status=400)
    
    # Execute the SQL query
    with connection.cursor() as cursor:
        cursor.execute(query_string, params)
        query_result = cursor.fetchall()
    # Create a list of dictionaries that represent the query result
    result_list = []
    # Get the column names
    column_names = [desc[0] for desc in cursor.description]

    # Loop through the query result and create a dictionary for each row
    for row in query_result:
        result_dict = {}
        for i, value in enumerate(row):
            result_dict[column_names[i]] = value
        result_list.append(result_dict)
            
    if result_list:
        # Return the query result in JSON format with success status code
        return JsonResponse(result_list, safe=False, status=200)
    else:
        # Return an error response with appropriate status code
        return JsonResponse({'error': 'No data found'}, status=404)