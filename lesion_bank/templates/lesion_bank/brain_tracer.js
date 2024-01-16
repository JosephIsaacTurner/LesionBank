<script src="https://cdnjs.cloudflare.com/ajax/libs/paper.js/0.12.11/paper-full.min.js"></script>

class PapayaSegmenter {
    // Class to handle in-browser segmentation of 3d volumes in Papaya

    constructor(viewer=papayaContainers[0].viewer,canvas=document.querySelector("canvas"), papayaPrototype=papaya.viewer.Viewer.prototype) {
        this.lassoList = [];
        this.worldLassoList = [];
        this.overall_points = [];
        this.viewer = viewer
        this.canvas = canvas
        this.papayaPrototype = papayaPrototype
        this.viewer.drawViewer = this.drawViewer.bind(this);
        this.checkCanvasExists();
    }

    clearAll() {
        // Method to clear all lassos and points from the viewer
        this.lassoList = [];
        this.worldLassoList = [];
        this.overall_points = [];
        this.viewer.drawViewer();
    }

    lassoTool(canvas) {
        // Method to create a lasso tool on the canvas
        function drawPath(ctx, points) {
            // Function create a path from the points array and draw it on the canvas
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (var i = 1; i < points.length; i++) {
            ctx.lineTo(points[i].x, points[i].y);
            }
            ctx.stroke();
        }
        var points = [];
        var isDrawing = false;
        var ctx = canvas.getContext('2d');
        canvas.addEventListener("mousedown", function(e) {
            isDrawing = true;
            points.push({
                x: e.offsetX,
                y: e.offsetY,
            });
        });
        canvas.addEventListener("mousemove", function(e) {
            if (!isDrawing) return;
            points.push({
                x: e.offsetX,
                y: e.offsetY,
            });
            drawPath(ctx, points);
        });
        canvas.addEventListener("mouseup", function() {
        isDrawing = false;
        var path = new Path2D();
        path.moveTo(points[0].x, points[0].y);
            for (var i = 1; i < points.length; i++) {
                path.lineTo(points[i].x, points[i].y);
        }
        ctx.fillStyle = "red";
        ctx.fill(path);
        var lassoPoints = [];
        for (var i = 0; i < points.length; i++) {
            lassoPoints.push([points[i].x, points[i].y]);
        }
        if (typeof callback === "function") {
            this.addToLassoList(lassoPoints);
        }
        points = [];
        });
    }

    addToLassoList(lassoPoints) {
        // Method to convert the screen points defined by lasso boundaries into image coordinates
        // Only adds points that are in the main slice (axial)
        let lasso = [];        
        lassoPoints.forEach(point => {
            let cursorPosition = this.viewer.cursorPosition
            let newPoint = {
                x: this.viewer.convertScreenToImageCoordinateX(point[0], this.viewer.axialSlice),
                y: this.viewer.convertScreenToImageCoordinateY(point[1], this.viewer.axialSlice),
                z: cursorPosition.z
            };
            if(this.viewer.intersectsMainSlice(newPoint)){
                if (!lasso.some(existingPoint => existingPoint.x === newPoint.x && existingPoint.y === newPoint.y && existingPoint.z === newPoint.z)) {
                    lasso.push(newPoint);
                }
            }
        });
        this.lassoList.push(lasso);
    }

    checkCanvasExists() {
        // Method to check if the canvas exists, and if it does, add the lassoTool to it
        // If not, wait 1 second and try again
        if (this.canvas) {
            this.lassoTool(this.canvas);

            this.canvas.addEventListener('mouseup', () => {
                this.checkLassoList();
            });
        } else {
            setTimeout(() => this.checkCanvasExists(), 1000);
        }
    }

    // Later on we will have to pull this out of the class, because it doesn't generalize to other use cases
    checkLassoList(){
        // Method to see if the lassoList is empty or not, and if it is, disable the nifti button
        var niftiButton = document.getElementById('createNifti');
        if(this.lassoList.length>0){
            niftiButton.classList.remove("disabled");
        }
        else{
            niftiButton.classList.add("disabled");
        }
    }

    drawViewer() {
        // Method to draw the viewer and the lasso outlines when the viewer is updated
        var result = this.papayaPrototype.drawViewer.apply(this.viewer, arguments);
        for (var i = 0; i < this.lassoList.length; i++) {
            let screenPoints = [];
            this.lassoList[i].forEach(point => {
                if (this.viewer.intersectsMainSlice(point)) {
                    var screenCoor = this.viewer.convertCoordinateToScreen(point);
                    screenPoints.push(screenCoor);
                }
            });
            if (screenPoints.length > 1) {
                var path = new Path2D();
                path.moveTo(screenPoints[0].x, screenPoints[0].y);
                for (var j = 1; j < screenPoints.length; j++) {
                    path.lineTo(screenPoints[j].x, screenPoints[j].y);
                }
                var ctx = this.viewer.context;
                ctx.fillStyle = "red";
                ctx.fill(path);
            }
        }
        return result;
    }
    
    lassoToWorld() {
        // Method to convert points defining the lassos into world coordinates
        this.worldLassoList = []
        this.lassoList.forEach(lasso => {
            let worldLasso = []
            lasso.forEach(point => {
                let worldPoint = this.viewer.getWorldCoordinateAtIndex(point.x, point.y, point.z, new papaya.core.Coordinate());
                worldLasso.push({'x':worldPoint.x,'y':worldPoint.y,'z':worldPoint.z})
            });
            this.worldLassoList.push(worldLasso);
        });
        return this.worldLassoList;
    }

    pointsInPolygon(polygonPoints, width = 1000, height = 1000) {
        // Method to find all points within a polygon
        // We use this to fill in the points defined by the lasso boundaries
        var myScope = new paper.PaperScope();
        myScope.setup(new myScope.Size(width, height));
        var path = new myScope.Path();
        polygonPoints.forEach(function(point) {
            path.add(new myScope.Point(point.x, point.y));
        });
        path.closed = true;
        var bounds = path.bounds;
        var insidePoints = [];
        for (var x = bounds.left; x < bounds.right; x++) {
            for (var y = bounds.top; y < bounds.bottom; y++) {
                var point = new myScope.Point(x, y);

                if (path.contains(point)) {
                    insidePoints.push({x: x, y: y});
                }
            }
        }
        let total_points = []
        insidePoints.forEach(point => {
            total_points.push({x:point.x, y:point.y, z:polygonPoints[0]['z']});
        });
        return total_points;
    }

    getOverallPoints() {
        // For each lasso in the list, convert it to world coordinates
        // Then find each point in the polygon and add it to the overall_points list
        this.lassoToWorld();
        this.overall_points = [];
        this.worldLassoList.forEach(sub_list => {
            let point_list = this.pointsInPolygon(sub_list);
            point_list.forEach(inner_point =>{
                if(!this.overall_points.some(op => op.x === inner_point.x && op.y === inner_point.y && op.z === inner_point.z)){
                    this.overall_points.push(inner_point);
                }
            });
        });
        this.overall_points = this.overall_points.map(point => [point.x, point.y, point.z,1]);
        return this.overall_points;
    }
}