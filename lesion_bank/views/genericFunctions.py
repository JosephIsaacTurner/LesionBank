from django.db import connection

def execute_query(statement, params=None):
    with connection.cursor() as cursor:
        cursor.execute(statement, params)
        rows = cursor.fetchall()
        column_names = [col[0] for col in cursor.description]  # get column names
    return column_names, rows

def fetch_results_and_column_names(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        column_names = [col[0] for col in cursor.description] # get column names
    return [rows, column_names]

def fetch_all_rows(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
    # Convert the query results into an HTML string
    html_string = ''.join([result[0] for result in results])
    return html_string

def fetch_single_row(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()

    if row is None:
        return None

    return {columns[i]: row[i] for i in range(len(columns))}

def getHTMLString():
    genericHTMLPath = "/home/django/django_project/staticfiles/genericHTML.html"
    if genericHTMLPath:
            with open(genericHTMLPath, 'r') as f:
                html_string = f.read()
    return html_string

callCount = 0

def make_thead(column_names, loadimage):
    thead = ""
    thead += "<thead><tr><th></th>"
    for col_name in column_names:
        if col_name in ["tracing_file_name", "network_file_name","lesion_id"]:
            pass
        else:
            thead += "<th>{}</th>".format(col_name.title())  # add column names as table headers
    if loadimage is True:
        thead += "<th>View</th>"
    thead += "</tr></thead>"
    return thead.replace("\n","")

def make_tbody(column_names, rows, type, loadimage, negative):
    eyeSymbol = f"""<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-eye-fill" viewBox="0 0 16 16">
            <path  d="M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/>
            <path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8zm8 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/>
            </svg>"""
    tbody = ""
    for j, row in enumerate(rows):
        trow = f"<tr class='tableRow tableRow{j}'><td>{j+1}</td>"
        for i, value in enumerate(row):
            col_name = column_names[i]  # get column name
            if col_name in ["tracing_file_name", "network_file_name","lesion_id"]:
                if col_name == "tracing_file_name" and type == "tracing" and loadimage is True:
                    nifti = value
                elif col_name == "network_file_name" and type == "network" and loadimage is True:
                    nifti = value
            else:
                if col_name.lower() in ["author", "symptom"]:
                    if col_name.lower() == "author":
                        page_name = "cases"
                    elif col_name == "symptom":
                        page_name = "symptoms"
                    else:
                        page_name = col_name
                    value = f"<a href='../{page_name}/?{col_name}={value}'>{value}</a>"
                trow += "<td>{}</td>".format(value)  # add column name and value to table cell
        if loadimage is True:
            if type == "tracing":
                trow += f"<td><button type='button' class='btn tracing btn-outline-secondary overlayOption activeReplace' nifti='{nifti}' imageType='tracing'>{eyeSymbol}</button></td>"
            elif type == "network":
                if negative:
                    corr = "negative"
                else:
                    corr = "positive"
                trow += f"<td><button type='button' class='btn network btn-outline-secondary overlayOption activeReplace' nifti='{nifti}' imageType='network' correlationType='{corr}'>{eyeSymbol}</button></td>"
        trow += "</tr>"
        tbody += f""",{j}:`{trow}`"""
    tbody = f"{'{' +tbody.replace(',','',1) + '}'}"
    return  tbody.replace('\n','')

def query_to_table_improved(statement, params, type=False, loadimage=False, negative=False, loadJson=False):
    global callCount
    if callCount > 8:
        callCount = 0
    callCount += 1
    # Execute a SQL query
    column_names, rows = execute_query(statement, params)
    # Check if rows are empty
    if not rows:
        return f"<i>No results found</i><br><script>console.log('unsuccesful with query: `{statement}`');</script>"
    
    # Create an HTML table to display the results
    thead = make_thead(column_names, loadimage)
    tbody = make_tbody(column_names, rows, type, loadimage, negative)

    tableHTML = f"""
    <div>
        <table class='table table-striped'>
        {thead}
            <tbody>
            <span></span>
            </tbody>
        </table>
    </div>"""

   
    html = f"""
                    <div class='queryTable' id='tableContainer{callCount}'>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center text-muted">
                        Show&nbsp;<select id="rows-displayed-select{callCount}" class="form-control mr-2 w-25 rowsDisplayedCount">"""
    optionArray = [1,2,3,4,5,6,7,8,9,10,15,20,30,50,80,100,120,150,180]
    if type == "tracing":
        rowDefault = 10
    elif type == "list":
        rowDefault = 30
    else:
        rowDefault = 10
    for i, value in enumerate(optionArray):
        if value >= len(rows) and value < rowDefault:
            html += f"""<option selected value="{value}">{value}</option>"""
            break
        elif value == rowDefault:
            html += f"""<option selected value="{value}">{value}</option>"""
            if value >= len(rows):
                break
        elif value >= len(rows):
            html += f"""<option value="{value}">All</option>"""
            break
        else:
            html += f"""<option value="{value}">{value}</option>"""
    html += f"""
                        </select>
                        <span class="text-muted flex-shrink-0">&nbsp;entries of {len(rows)}</span>
                    </div>
                    <ul class="pagination justify-content-end">
                        <li class="page-item"><a class="page-link" data='tableContainer{callCount}' onclick='tableActivator(event, "First"); event.preventDefault();' href="#" id="prev-btn{callCount}">First</a></li>
                        <li class="page-item"><a class="page-link " data= 'tableContainer{callCount}' onclick='tableActivator(event, "Previous"); event.preventDefault();' href="#" id="page-1{callCount}">Previous</a></li>
                        <li class="page-item"><a class="page-link" data = 'tableContainer{callCount}' onclick='tableActivator(event, "Next"); event.preventDefault();' href="#" id="page-2{callCount}">Next</a></li>
                        <li class="page-item"><a class="page-link" data = 'tableContainer{callCount}'onclick='tableActivator(event, "Last"); event.preventDefault();' href="#" id="page-3{callCount}">Last</a></li>
                    </ul>
                </div>            
            """
    html += f"""
    <script>
        var tableHTML = `{tableHTML}`;
        var tbody = {tbody};
        """  + f"""
        var rowCountId = 'rows-displayed-select{callCount}';
        var tableContainerId = 'tableContainer{callCount}';
        // insertTableRows(tableContainerId, tableHTML, tbody, 4);
            """ + """
        tableObject = {'tableContainerId':tableContainerId,'rowCountId':rowCountId, 'tableHTML':tableHTML, 'tbody':tbody};
        document.getElementById(tableContainerId).setAttribute('data-my-object', JSON.stringify(tableObject));
    </script>
    """
    # Return the HTML table
    return html


def query_to_table(statement, type=False, loadimage=False, negative=False, loadJson=False):
    global callCount
    if callCount > 8:
        callCount = 0
    callCount += 1
    # Execute a SQL query
    column_names, rows = execute_query(statement)
    # Check if rows are empty
    if not rows:
        return f"<i>No results found</i><br><script>console.log('unsuccesful with query: `{statement}`');</script>"
    
    # Create an HTML table to display the results
    thead = make_thead(column_names, loadimage)
    tbody = make_tbody(column_names, rows, type, loadimage, negative)

    tableHTML = f"""
    <div>
        <table class='table table-striped'>
        {thead}
            <tbody>
            <span></span>
            </tbody>
        </table>
    </div>"""

   
    html = f"""
                    <div class='queryTable' id='tableContainer{callCount}'>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center text-muted">
                        Show&nbsp;<select id="rows-displayed-select{callCount}" class="form-control mr-2 w-25 rowsDisplayedCount">"""
    optionArray = [1,2,3,4,5,6,7,8,9,10,15,20,30,50,80,100,120,150,180]
    if type == "tracing":
        rowDefault = 10
    elif type == "list":
        rowDefault = 30
    else:
        rowDefault = 10
    for i, value in enumerate(optionArray):
        if value >= len(rows) and value < rowDefault:
            html += f"""<option selected value="{value}">{value}</option>"""
            break
        elif value == rowDefault:
            html += f"""<option selected value="{value}">{value}</option>"""
            if value >= len(rows):
                break
        elif value >= len(rows):
            html += f"""<option value="{value}">All</option>"""
            break
        else:
            html += f"""<option value="{value}">{value}</option>"""
    html += f"""
                        </select>
                        <span class="text-muted flex-shrink-0">&nbsp;entries of {len(rows)}</span>
                    </div>
                    <ul class="pagination justify-content-end">
                        <li class="page-item"><a class="page-link" data='tableContainer{callCount}' onclick='tableActivator(event, "First"); event.preventDefault();' href="#" id="prev-btn{callCount}">First</a></li>
                        <li class="page-item"><a class="page-link " data= 'tableContainer{callCount}' onclick='tableActivator(event, "Previous"); event.preventDefault();' href="#" id="page-1{callCount}">Previous</a></li>
                        <li class="page-item"><a class="page-link" data = 'tableContainer{callCount}' onclick='tableActivator(event, "Next"); event.preventDefault();' href="#" id="page-2{callCount}">Next</a></li>
                        <li class="page-item"><a class="page-link" data = 'tableContainer{callCount}'onclick='tableActivator(event, "Last"); event.preventDefault();' href="#" id="page-3{callCount}">Last</a></li>
                    </ul>
                </div>            
            """
    html += f"""
    <script>
        var tableHTML = `{tableHTML}`;
        var tbody = {tbody};
        """  + f"""
        var rowCountId = 'rows-displayed-select{callCount}';
        var tableContainerId = 'tableContainer{callCount}';
        // insertTableRows(tableContainerId, tableHTML, tbody, 4);
            """ + """
        tableObject = {'tableContainerId':tableContainerId,'rowCountId':rowCountId, 'tableHTML':tableHTML, 'tbody':tbody};
        document.getElementById(tableContainerId).setAttribute('data-my-object', JSON.stringify(tableObject));
    </script>
    """
    # Return the HTML table
    return html

def getJavascript(x=0,y=0,z=0):
    javascript = """
                <script>


                    function expandColorPalette(colors) {
                        var expandedPalette = [];

                        for (var i = 0; i < colors.length - 1; i++) {
                            var currentColor = colors[i];
                            var nextColor = colors[i + 1];

                            // Convert the colors to RGBA format
                            var currentRGBA = hexToRGBA(currentColor);
                            var nextRGBA = hexToRGBA(nextColor);

                            // Calculate the color step values
                            var stepR = (nextRGBA.r - currentRGBA.r) / 5;
                            var stepG = (nextRGBA.g - currentRGBA.g) / 5;
                            var stepB = (nextRGBA.b - currentRGBA.b) / 5;
                            var stepA = (nextRGBA.a - currentRGBA.a) / 5;

                            // Generate 5 intervening colors between the current and next color
                            for (var j = 0; j < 5; j++) {
                            var interpolatedColor = interpolateColor(currentRGBA, stepR, stepG, stepB, stepA, j);
                            expandedPalette.push(rgbaToHex(interpolatedColor));
                            }
                        }

                        // Add the last color from the original palette
                        expandedPalette.push(colors[colors.length - 1]);

                        return expandedPalette;
                        }

                        // Helper function to convert hex color to RGBA format
                        function hexToRGBA(hex) {
                        var bigint = parseInt(hex.substr(1), 16);
                        var r = (bigint >> 24) & 255;
                        var g = (bigint >> 16) & 255;
                        var b = (bigint >> 8) & 255;
                        var a = bigint & 255;
                        return { r: r, g: g, b: b, a: a };
                        }

                        // Helper function to convert RGBA color to hex format
                        function rgbaToHex(rgba) {
                        var hexR = rgba.r.toString(16).padStart(2, '0');
                        var hexG = rgba.g.toString(16).padStart(2, '0');
                        var hexB = rgba.b.toString(16).padStart(2, '0');
                        var hexA = rgba.a.toString(16).padStart(2, '0');
                        return '#' + hexR + hexG + hexB + hexA;
                        }

                        // Helper function to interpolate color based on step values
                        function interpolateColor(color, stepR, stepG, stepB, stepA, step) {
                        return {
                            r: Math.round(color.r + stepR * step),
                            g: Math.round(color.g + stepG * step),
                            b: Math.round(color.b + stepB * step),
                            a: Math.round(color.a + stepA * step)
                        };
                    }

                    function limitOverlayCount(n) {
                        let activeCount = 0;
                        const queryTables = document.querySelectorAll('.queryTable');
                        const tbody = tableObject.tbody;

                       
                        queryTables.forEach((table, index) => {
                            let tableObject = JSON.parse(table.getAttribute('data-my-object'));
                            
                            const overlayOptions = table.querySelectorAll('.overlayOption');

                            if (index === 0 && overlayOptions.length < 20) {
                                overlayOptions.forEach((option, i) => {
                                    if (i < 1 && activeCount < n) {
                                        tableRow = tableObject.tbody[i];
                                        if(tableRow.includes("activeReplace")){
                                            tableRow = tableRow.replace("activeReplace","active");
                                        }
                                        else if(tableRow.includes("active")){
                                            tableRow = tableRow.replace("active","activeReplace");
                                        }
                                        tableObject.tbody[i] = tableRow;
                                        table.setAttribute('data-my-object', JSON.stringify(tableObject));


                                        option.classList.add('active');
                                        activeCount++;
                                    }
                                });
                            } else {
                            overlayOptions.forEach((option, i) => {
                                if (i < 1 && activeCount < n) {
                                
                                tableRow = tableObject.tbody[i];
                                if(tableRow.includes("activeReplace")){
                                    tableRow = tableRow.replace("activeReplace","active");
                                }
                                else if(tableRow.includes("active")){
                                    tableRow = tableRow.replace("active","activeReplace");
                                }
                                tableObject.tbody[i] = tableRow;
                                table.setAttribute('data-my-object', JSON.stringify(tableObject));

                                option.classList.add('active');
                                activeCount++;
                                }
                            });
                            }
                        });
                    }

                    function addFunction(){
                        const menuButtons = document.querySelectorAll('.papaya-toolbar');
                        menuButtons.forEach((button, index) => {
                            button.addEventListener('click', () => {
                                addToolTipToMenuButtons();
                            });
                        });
                    }
                    
                    function addToolTipToMenuButtons() {
                        var images = getImagePath()[0];
                        images = images.reverse();

                        const menuButtons = document.querySelectorAll('.papaya-menu-button');
                        menuButtons.forEach((button, index) => {
                            button.style.display = 'inline-block';
                            const tooltip = document.createElement('div');
                            tooltip.className = 'myTooltip'; 
                            tooltip.textContent = images[index]; 
                            tooltip.style.display = 'none';
                            tooltip.style.position = 'fixed';
                            tooltip.style.zIndex = '100';
                            tooltip.style.backgroundColor = '#222';
                            tooltip.style.color = '#b5cbd3';
                            tooltip.style.padding = '6px';
                            tooltip.style.border = 'solid 2px darkgray';
                            tooltip.style.borderRadius = '5px';
                            tooltip.style.fontSize = '14px';
                            tooltip.style.fontFamily = 'sans-serif';
                            tooltip.style.boxSizing = 'content-box';
                            button.addEventListener('mouseover', () => {
                                tooltip.style.display = 'block';
                                const buttonRect = button.getBoundingClientRect();
                                tooltip.style.top = `${buttonRect.top - tooltip.offsetHeight}px`;
                                tooltip.style.left = `${buttonRect.left}px`;
                                tooltip.style.display = 'block';
                            });
                            button.addEventListener('mouseout', () => {
                                tooltip.style.display = 'none';
                            });
                            button.appendChild(tooltip);
                            // Position the tooltip next to the hovered element.
                            const rect = button.getBoundingClientRect();
                            tooltip.style.top = `${rect.top - tooltip.offsetHeight}px`;
                            tooltip.style.left = `${rect.left + button.offsetWidth}px`;
                        });
                    }

                    function reloadViewer(allImages){
                        const negCount = allImages[1];
                        allImages = allImages[0];
                        let overlayCount = 0;
                        let networkCount = 0;
                        const imagePath = allImages.map((image) => `../static/MRIData/GZippedEverything/${image}.gz`);

                        var params = [];
                            params['images'] = imagePath;
                            params["luts"] = [];
                            const options = [
                                [[0, 0.9, 0.2, 0.2], [1, 1, 0.2, 0.2]],
                                [[0, 0.2, 0.9, 0.2], [1, 0.2, 1, 0.2]],
                                [[0, 0.2, 0.2, 0.9], [1, 0.2, 0.2, 1]],
                                [[0, 0.9, 0.9, 0.2], [1, 1, 1, 0.2]],
                                [[0, 0.9, 0.2, 0.2], [1, 1, 0.2, 0.2]],
                                [[0, 0.2, 0.9, 0.2], [1, 0.2, 1, 0.2]],
                                [[0, 0.2, 0.2, 0.9], [1, 0.2, 0.2, 1]],
                                [[0, 0.9, 0.9, 0.2], [1, 1, 1, 0.2]],
                            ];
                            for (let i = 0; i < options.length; i++) {
                                const option = options[i];
                                for (let j = 0; j < option.length; j++) {
                                    const values = option[j];
                                    for (let k = 0; k < values.length; k++) {
                                        if (values[k] === 0.2) {
                                            values[k] += Math.random() * 0.5;
                                        }
                                    }
                                }
                            }

                            let optionIndex = 0;
                            for (let i = 0, optionIndex = 0; i < allImages.filter((element) => element.toLowerCase().includes('tracing')).length; i++, optionIndex++) {
                                const option = options[optionIndex % options.length];
                                const newData = option.map(arr => arr.map(val => val === 0.2 ? val + 0.4 : val));
                                params["luts"].push({"name": "tracing" + i.toString(), "data": newData});
                                if (optionIndex === options.length) {
                                    optionIndex = 0;
                                }
                            }
                            const overlayLutData = [
                                [[0,.75,0,0],[.5,1,.5,0],[.95,1,1,0],[1,1,1,1]],
                                [[0,0,0,1],[.5,0,.5,1],[.95,0,1,1],[1,1,1,1]],
                                [[0,0,.75,0],[.5,.5,1,0],[.95,1,1,0],[1,1,1,1]],
                                [[0,.75,0,0],[.5,1,.5,0],[.95,1,1,0],[1,1,1,1]],
                                [[0,0,.75,0],[.5,.5,1,0],[.95,1,1,0],[1,1,1,1]],
                                [[0,0,0,.75],[.5,.5,0,1],[.95,1,0,1],[1,1,1,1]],
                                [[0,.75,0,0],[.5,1,.5,0],[.95,1,1,0],[1,1,1,1]],
                                [[0,0,.75,0],[.5,.5,1,0],[.95,1,1,0],[1,1,1,1]]
                            ];
                            for (let i = 0; i < overlayLutData.length; i++) {
                                const option = overlayLutData[i];
                                for (let j = 0; j < option.length; j++) {
                                    const values = option[j];
                                    for (let k = 0; k < values.length; k++) {
                                        if (j!=0 && (values[k] === 0 || values[k] === .5)) {
                                            values[k] += Math.random() * 0.5;
                                        }
                                    }
                                }
                            }
                            for (i = 0, optionIndex = 0; i < allImages.filter((element) => element.toLowerCase().includes('network')).length; i++, optionIndex++) {
                                const option = overlayLutData[optionIndex % options.length];
                                const newData = option.map(arr => arr.map(val => val === 0.2 ? val + 0.4 : val));
                                params["luts"].push({"name": "network" + i.toString(), "data": newData});
                                if (optionIndex === options.length) {
                                    optionIndex = 0;
                                }
                            }
                            params["luts"].push({"name":"PuBu", "data":[[0,1,0.968627,0.984314],[0.125,0.92549,0.905882,0.94902],[0.25,0.815686,0.819608,0.901961],[0.375,0.65098,0.741176,0.858824],[0.5,0.454902,0.662745,0.811765],[0.625,0.211765,0.564706,0.752941],[0.75,0.0196078,0.439216,0.690196],[0.875,0.0156863,0.352941,0.552941],[1,0.00784314,0.219608,0.345098]]});
                            params["luts"].push({"name":"OrRd", "data":[[0,1,0.968627,0.92549],[0.125,0.996078,0.909804,0.784314],[0.25,0.992157,0.831373,0.619608],[0.375,0.992157,0.733333,0.517647],[0.5,0.988235,0.552941,0.34902],[0.625,0.937255,0.396078,0.282353],[0.75,0.843137,0.188235,0.121569],[0.875,0.701961,0,0],[1,0.498039,0,0]]});

                            allImages.forEach(function(imageName, index) {
                                // Check if we are in the last N elements of the array
                                if (index >= allImages.length - negCount && imageName.toLowerCase().includes("network")) {
                                    params[imageName+'.gz'] =  {"min":30, "max":95, "lut":"PuBu", "alpha":"0.6"};
                                    // params[imageName+'.gz'] = {'min': 25, 'max': 100, 'alpha': 0.4, 'lut':'network'+networkCount.toString()};
                                    // params[imageName+'.gz'] = {"parametric": true,  "min":0, "lut":"OrRd", "negative_lut":"PuBu", "alpha":"0.75", "symmetric":true, minPercent: 0.0, maxPercent: 1.0};
                                    networkCount ++;
                                    //"min":0, "max":100, 
                                }
                                else if (imageName.toLowerCase().includes("network")){
                                    // params[imageName+'.gz'] = {'min': 25, 'max': 100, 'alpha': 0.4, 'lut':'network'+networkCount.toString()};
                                    //params[imageName+'.gz'] = {"parametric": true,  "min":0, "lut":"OrRd", "negative_lut":"PuBu", "alpha":"0.6", "symmetric":true, minPercent: 0.0, maxPercent: 1.0};
                                    params[imageName+'.gz'] =  {"min":30, "max":110, "lut":"OrRd", "alpha":"0.6"};
                                    networkCount ++; 
                                }
                                else if(imageName.toLowerCase().includes("tracing")){
                                    params[imageName+'.gz'] = {'lut':'tracing'+overlayCount.toString(), "alpha":1.0};
                                    overlayCount ++;
                                }                  
                            });

                            
                            params['worldSpace'] = true;""" + f"""
                            params['coordinate'] = [{x},{y},{z}];""" + """
                            // console.log(params['coordinate']);
                            params['syncOverlaySeries'] = false;
                            params['showOrientation'] = true;
                            params['showLowerCrosshairs'] = true;
                            params['loadingComplete'] = addToolTipToMenuButtons;
                            params['expandable'] = true;
                            params['showControls'] = false;
                            params['showControlBar'] = false;
                        papaya.Container.resetViewer(0, params);         
                        setTimeout(addFunction, 3500);
                        setTimeout(addToolTipToMenuButtons, 3500);
                    }

                    function getImagePath() {
                        const activeOverlayOptions = document.querySelectorAll('.overlayOption.active');
                        const networkImagesPos = [];
                        const networkImagesNeg = [];
                        const tracingImages = [];

                        activeOverlayOptions.forEach((option) => {
                            const niftiValue = option.getAttribute('nifti');
                            const imageType = option.getAttribute('imageType');
                            const correlationType = option.getAttribute('correlationType');
                            if (imageType === 'network') {
                                if (correlationType == 'positive'){
                                    networkImagesPos.push(niftiValue);
                                }
                                else if(correlationType == 'negative'){
                                    networkImagesNeg.push(niftiValue);
                                }
                            
                            } else if (imageType === 'tracing') {
                                tracingImages.push(niftiValue);
                            }
                        });

                        const allImages = ["GenericMNI.nii", ...tracingImages, ...networkImagesPos, ...networkImagesNeg];
                        return [allImages, networkImagesNeg.length];
                    }

                    setTimeout(() => {
                        reloadViewer(getImagePath());
                    }, 300);

                                """ + """
                    function insertTableRows(element) {
                        
                        const tableObject = JSON.parse(element.getAttribute('data-my-object'));
                        const tableContainerId = tableObject.tableContainerId;
                        const rowCountId = tableObject.rowCountId;
                        const tableHTML = tableObject.tableHTML;
                        const tbody = tableObject.tbody;

                        const rowCount = parseInt(document.getElementById(rowCountId).value);
                        // get the table container element
                        const tableContainer = document.getElementById(tableContainerId); 
                        tableContainer.innerHTML = "";

                        // calculate the number of table rows and table divs needed
                        const totalRows = Object.keys(tbody).length;
                        const totalDivs = Math.ceil(totalRows / rowCount);

                        // create and insert the table divs

                        let start = 0;
                        for (let i = 0; i < totalDivs; i++) {
                            // create a new div
                            const tableDiv = document.createElement('div');
                            uniqueClassName = tableContainerId;
                            tableDiv.classList.add('table-container');
                            tableDiv.classList.add(uniqueClassName);
                            tableDiv.innerHTML = tableHTML;

                            // get the tbody element of the table
                            const tbodyElem = tableDiv.querySelector('tbody');

                           // insert the table rows into the tbody element
                            if (rowCount === '1') {
                                const rowHTML = tbody[start];
                                tbodyElem.insertAdjacentHTML('beforeend', rowHTML);
                            } else {
                                for (let j = start; j < Math.min(parseInt(start) + parseInt(rowCount), parseInt(totalRows)); j++) {
                                    j = parseInt(j);
                                    const rowHTML = tbody[j];
                                    tbodyElem.insertAdjacentHTML('beforeend', rowHTML);
                                }
                            }


                            // insert the table div into the table container
                            tableContainer.appendChild(tableDiv);

                            // move the start index for the next div
                            start += rowCount;
                        }
                        uniqueClassSelector = '.' + uniqueClassName;
                        allTables = document.querySelectorAll(uniqueClassSelector);
                        for(let i = 0; i < allTables.length; i++) {
                            if(i == 0){
                                allTables[i].classList.add('visibleTable');
                            }
                            allTables[i].style.display = "none";                      
                        }
                        tableActivator(uniqueClassName, "First");
                        reloadOverlayJavascript();
                    }

                    function tableActivator(event, action){
                        let targetClass;
                        if (event instanceof PointerEvent) {
                            targetClass = (event && event.target.getAttribute('data')) || null;
                        }
                        else{
                            targetClass = event;
                        }
                        index = targetClass.charAt(targetClass.length - 1);
                        const divs = document.querySelectorAll(`div.${targetClass}`);
                        if(action == "First"){
                            for (let i = 0; i < divs.length; i++) {  
                                if (divs[i].classList.contains('visibleTable')) {
                                    divs[i].classList.toggle('visibleTable');
                                    divs[0].classList.toggle('visibleTable');
                                    break;
                                }
                            }                            
                        }
                        else if(action == "Previous"){
                            for (let i = 0; i < divs.length; i++) {
                                if (divs[i].classList.contains('visibleTable')) {
                                    divs[i].classList.toggle('visibleTable');
                                    const prevIndex = i === 0 ? divs.length - 1 : i - 1;
                                    divs[prevIndex].classList.toggle('visibleTable');
                                    break;
                                }
                            }
                        }
                        else if (action == "Next"){
                            for (let i = 0; i < divs.length; i++) {  
                                if (divs[i].classList.contains('visibleTable')) {
                                    divs[i].classList.toggle('visibleTable');
                                    const nextIndex = (i + 1) % divs.length;
                                    divs[nextIndex].classList.toggle('visibleTable');
                                    break;
                                }
                            }
                        }
                        else{
                            for (let i = 0; i < divs.length; i++) {  
                                if (divs[i].classList.contains('visibleTable')) {
                                    divs[i].classList.toggle('visibleTable');
                                    divs[divs.length-1].classList.toggle('visibleTable');
                                    break;
                                }
                            }
                        }

                        for (let i = 0; i < divs.length; i++) {
                            if (divs[i].classList.contains('visibleTable')) {
                                divs[i].style.display = "block";  
                                if (i === 0) {
                                    document.getElementById('prev-btn' + index).classList.add('disabled');
                                    document.getElementById('page-1' + index).classList.add('disabled');
                                } else {
                                    document.getElementById('prev-btn' + index).classList.remove('disabled');
                                    document.getElementById('page-1' + index).classList.remove('disabled');
                                }
                                if (i === divs.length-1) {
                                    document.getElementById('page-2' + index).classList.add('disabled');
                                    document.getElementById('page-3' + index).classList.add('disabled');
                                } else {
                                    document.getElementById('page-2' + index).classList.remove('disabled');
                                    document.getElementById('page-3' + index).classList.remove('disabled');                                    
                                }                   
                            }
                            else {
                                divs[i].style.display = "none";
                            }
                            // check if i is 0
                        }
                    } 

                    function addJavascriptToOverlays(event){
                            reloadViewer(getImagePath());

                            // this is what I care about
                            const parent = event.target.parentNode;
                            const grandparent = parent.parentNode;
                            const greatgrandparent = grandparent.parentNode;
                            const greatgreatgrandparent = greatgrandparent.parentNode;
                            const ancestor0 = greatgreatgrandparent.parentNode
                            const ancestor1 = ancestor0.parentNode;
                            const ancestor2 = ancestor1.parentNode;
                            const ancestor3 = ancestor2.parentNode;
                            const ancestor4 = ancestor3.parendeNode;

                            let list0 = grandparent.classList;
                            let list1 = greatgrandparent.classList;
                            let list2 = greatgreatgrandparent.classList;
                            // console.log(list0,list1,list2);

                            let rowClassList;

                            if(list0.contains('tableRow')){
                                rowClassList = list0;
                            }
                            else if(list1.contains('tableRow')){
                                rowClassList = list1;
                            }
                            else if(list2.contains('tableRow')){
                                rowClassList = list2;
                            }
                            // console.log(rowClassList);
                            let classList;
                            let classList0 = ancestor1.classList;
                            let classList1 = ancestor2.classList;
                            let classList2 = ancestor3.classList;
                            if(classList2.contains('table-container')){
                                classList = classList2;
                            }
                            else{
                                classList = classList0;
                            }
                            if (classList.length === 0) {
                                classList = classList1;
                            }
                            parentClass = classList[1];
                            rowClass = rowClassList[1];
                            let index = parentClass.charAt(parentClass.length -1);
                            let rowIndex = rowClass.charAt(rowClass.length -1);
                            let parentTableId = 'tableContainer' + index;
                            let tableContainer = document.getElementById(parentTableId);
                            let tableObject = JSON.parse(tableContainer.getAttribute('data-my-object'));
                            tableRow = tableObject.tbody[rowIndex];
                            if(tableRow.includes("activeReplace")){
                                tableRow = tableRow.replace("activeReplace","active");
                            }
                            else if(tableRow.includes("active")){
                                tableRow = tableRow.replace("active","activeReplace");
                            }

                            tableObject.tbody[rowIndex] = tableRow;
                            tableContainer.setAttribute('data-my-object', JSON.stringify(tableObject));
                            // tableContainer =  document.getElementById(parentTableId);
                            // updatedData = tableContainer.getAttribute('data-my-object');
                            // updatedObject = JSON.parse(updatedData);
                            // console.log(updatedObject.tbody[rowIndex]);
                    }


                    const queryTables = document.querySelectorAll('.queryTable');
                    queryTables.forEach((queryTable) => {
                        const tableObject = JSON.parse(queryTable.getAttribute('data-my-object'));
                        insertTableRows(queryTable);
                        const rowCounter = document.getElementById(tableObject.rowCountId);
                        rowCounter.addEventListener('change', () => {
                            insertTableRows(queryTable);
                        });

                    });
                   
                    function reloadOverlayJavascript() {
                        let overlayOptions = document.querySelectorAll('button.overlayOption');
                        overlayOptions.forEach((option) => {
                            if (!option.classList.contains('js-added')) {
                                option.addEventListener('click', (event) => {
                                    option.classList.toggle("active");
                                    addJavascriptToOverlays(event);
                                });
                                option.classList.add('js-added');
                            }
                        });
                    }

                    function enablePoppers() {
                        let popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
                        let popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
                        return "poppers enabled";
                    }

                    enablePoppers();
                    reloadOverlayJavascript();
                    limitOverlayCount(8);

                </script>""" 
    return javascript