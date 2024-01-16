class PapayaSegmenter {
    constructor(viewer = null, canvas = null, papayaPrototype = null) {
        this.initialize(viewer, canvas, papayaPrototype);
    }

    initialize(viewer, canvas, papayaPrototype) {
        // Method to initialize the segmenter and retry if any elements are not found
        if (canvas === null) {
            canvas = document.querySelector("canvas");
        }
        if (viewer === null && papayaContainers && papayaContainers.length > 0) {
            viewer = papayaContainers[0].viewer;
        }
        if (papayaPrototype === null && papaya && papaya.viewer && papaya.viewer.Viewer) {
            papayaPrototype = papaya.viewer.Viewer.prototype;
        }

        if (viewer && canvas && papayaPrototype) {
            // If all elements are found, initialize the segmenter
            this.lassoList = [];
            this.worldLassoList = [];
            this.voxels = [];
            this.viewer = viewer;
            this.canvas = canvas;
            this.papayaPrototype = papayaPrototype;
            this.viewer.drawViewer = this.drawViewer.bind(this);
            this.lassoTool();
        } else {
            // If any element is not found, retry after a delay
            setTimeout(() => this.initialize(viewer, canvas, papayaPrototype), 1000); // Retry after 1 second
        }
    }

    clearAll() {
        // Method to clear all lassos and points from the viewer
        this.lassoList = [];
        this.worldLassoList = [];
        this.voxels = [];
        this.viewer.drawViewer();
    }

    lassoTool() {
        // Method to create a lasso tool on the canvas
        const drawPath = (points, ctx) => {
            ctx.strokeStyle = 'magenta';
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (var i = 1; i < points.length; i++) {
                let testPoint = {
                    x: this.viewer.convertScreenToImageCoordinateX(points[i].x, this.viewer.axialSlice),
                    y: this.viewer.convertScreenToImageCoordinateY(points[i].y, this.viewer.axialSlice),
                    z: this.viewer.cursorPosition.z
                };
                if (this.viewer.intersectsMainSlice(testPoint)) {
                    ctx.lineTo(points[i].x, points[i].y);
                }
            }
            ctx.stroke();
        };
        var points = [];
        var isDrawing = false;
        let ctx = this.canvas.getContext('2d');
        this.canvas.addEventListener("mousedown", function(e) {
            isDrawing = true;
            points.push({
                x: e.offsetX,
                y: e.offsetY,
            });
        });
        this.canvas.addEventListener("mousemove", function(e) {
            if (!isDrawing) return;
            points.push({
                x: e.offsetX,
                y: e.offsetY,
            });
            drawPath(points, ctx, this.viewer);
        });
        this.canvas.addEventListener("mouseup", (e) => {
            isDrawing = false;
            var path = new Path2D();
            path.moveTo(points[0].x, points[0].y);
            for (var i = 1; i < points.length; i++) {
                let testPoint = {
                    x: this.viewer.convertScreenToImageCoordinateX(points[i].x, this.viewer.axialSlice),
                    y: this.viewer.convertScreenToImageCoordinateY(points[i].y, this.viewer.axialSlice),
                    z: this.viewer.cursorPosition.z
                }
                if (this.viewer.intersectsMainSlice(testPoint)) {
                    console.log("point in main slice");
                    path.lineTo(points[i].x, points[i].y);
                }
                else{
                    console.log("Point not in main slice");
                }
                // path.lineTo(points[i].x, points[i].y);
            }
            ctx.fillStyle = "red";
            ctx.fill(path);
            var lassoPoints = [];
            for (var i = 0; i < points.length; i++) {
                lassoPoints.push([points[i].x, points[i].y]);
            }
            this.addToLassoList(lassoPoints);
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

    getVoxels() {
        // For each lasso in the list, convert it to world coordinates
        // Then find each point in the polygon and add it to the overall_points list
        this.lassoToWorld();
        this.voxels = [];
        this.worldLassoList.forEach(sub_list => {
            let point_list = this.pointsInPolygon(sub_list);
            point_list.forEach(inner_point =>{
                if(!this.voxels.some(op => op.x === inner_point.x && op.y === inner_point.y && op.z === inner_point.z)){
                    this.voxels.push(inner_point);
                }
            });
        });
        this.voxels = this.voxels.map(point => [point.x, point.y, point.z,1]);
        return this.voxels;
    }
}