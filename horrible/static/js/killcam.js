/*jshint esversion: 6 */
var  kill_id  = 11;
var MAX_POINTS;
var renderer, scene, camera, controls, line, drawCount, killer_obj, coords,
     something, prog, look_at_pt, render, animate, light;
var tubes = [];
var pause = false;
var elem = document.getElementById('killcam_div');
var look = "target";
var follow = 'weapon';

function get_window_size() {
    var width = window.innerWidth * 0.9;
    var height = window.innerHeight * 0.9;
    var dim = {
        'height': height,
        'width': width
    };
    return dim;
}


var params = {
    width: 20,
    animationView: false,
    lookAhead: false,
    cameraHelper: false,
    'radius': 10,
};


function addFloor() {
    var floorGeometry = new THREE.PlaneGeometry(100000, 100, 20, 20);
    var floorMaterial = new THREE.MeshPhongMaterial();
    floorMaterial.map = THREE.ImageUtils.loadTexture("../assets/textures/floor_2-1024x1024.png");

    floorMaterial.map.wrapS = floorMaterial.map.wrapT = THREE.RepeatWrapping;
    floorMaterial.map.repeat.set(8, 8);
    var floorMesh = new THREE.Mesh(floorGeometry, floorMaterial);
    floorMesh.receiveShadow = true;
    floorMesh.rotation.x = -0.5 * Math.PI;
    scene.add(floorMesh);
}



function tube_prep(data, color, init_step, name, max_pt) {

    var points = [];
    for (var i = 0, l = data.length; i < l; i++) {
        points.push(new THREE.Vector3(...data[i]));
    }

    var curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.05);

    var line_points = curve.getPoints(max_pt);


    var max_pt1 = max_pt+1;
    var widthSteps = 1;

    let pts2 = curve.getPoints(max_pt);
    pts2.forEach(p => {
        p.z += params.width;
    });
    pts = line_points.concat(pts2);

    var ribbonGeom = new THREE.BufferGeometry().setFromPoints(pts);

    var indices = [];
    for (iy = 0; iy < widthSteps; iy++) { // the idea taken from PlaneBufferGeometry
        for (ix = 0; ix < max_pt; ix++) {
            var a = ix + max_pt1 * iy;
            var b = ix + max_pt1 * (iy + 1);
            var c = (ix + 1) + max_pt1 * (iy + 1);
            var d = (ix + 1) + max_pt1 * iy;
            indices.push(a, b, d);
            indices.push(b, c, d);
        }
    }
    ribbonGeom.setIndex(indices);
    ribbonGeom.computeVertexNormals();

    var ribbon = new THREE.Mesh(ribbonGeom, new THREE.MeshBasicMaterial({
        side: THREE.DoubleSide, color: color
    }));
    ribbon.geometry.setDrawRange(0, 0);
    scene.add(ribbon);

    var sphere = new THREE.Mesh(
        new THREE.SphereBufferGeometry(15, 10, 10, 0, Math.PI * 2, 0, Math.PI * 2),
        new THREE.MeshBasicMaterial({color: color}));
    sphere.updateMatrix();
    scene.add(sphere);

    val = {
        'line_points': line_points,
        'draw_max': line_points.length*3*2,
        'drawCount': init_step,
        'pos_idx': 0,
        'sphere': sphere,
        'ribbon': ribbon,
        'name': name
    };

    return val;
}


function make_circle_floor(target){
    var plane_geo = new THREE.CircleBufferGeometry( 100000, 10 );
    var plane_mat = new THREE.MeshBasicMaterial( {color: 'black', side: THREE.DoubleSide, transparent:true, opacity: 0.25} );
    var plane_1 = new THREE.Mesh( plane_geo, plane_mat );
    var plane_wire = new THREE.MeshBasicMaterial( {color: 'black', wireframe: true, transparent:true, opacity:0.25 } );
    var plane_2 = new THREE.Mesh( plane_geo, plane_wire );
    var plane = new THREE.Object3D();
    plane.add(plane_1);
    plane.add(plane_2);
    plane.lookAt(new THREE.Vector3(0, 1, 0));

    plane.position.set(
        target.line_points[target.line_points.length - 1].x,
        0,
        target.line_points[target.line_points.length - 1].z
    );
    scene.add( plane );
}

function makeCameraAndControls() {
    var dim = get_window_size();
    camera = new THREE.PerspectiveCamera(45, dim.width / dim.height, 0.01, 1000000);
    scene.camera = camera;
    // controls = new THREE.OrbitControls(camera, renderer.domElement);
    // controls.enableDamping = true;
    // controls.dampingFactor = 0.07;
    // controls.rotateSpeed = 0.05;
    // controls.zoomSpeed = 0.05;
    // controls.maxPolarAngle = Math.PI / 2 - 0.009;
    // controls.target = look_at_pt;
    // scene.controls = controls;
    // controls.addEventListener("change", () => {
    //     if (this.renderer) this.renderer.render(this.scene, camera);
    // });
}


function onWindowResize() {
    var dim = get_window_size();
    if (camera != null) {
        camera.aspect = dim.width / dim.height;
        renderer.setSize(dim.width, dim.height);
        camera.updateProjectionMatrix();
    }
}

var loadingManager = new THREE.LoadingManager();
loadingManager.onStart = function(){
    document.getElementById('load_spin').hidden = false;
};


loadingManager.onLoad = function() {
    document.getElementById('load_spin').hidden = true;
};

function getCenterPoint(obj) {
    var center = obj.boundingBox.getCenter();
    mesh.localToWorld( center );
    return center;
}

function set_camera(tube, look, follow){
    if (tube.name === look) {
        let pt = tube.line_points[tube.pos_idx];
        camera.lookAt(pt.x, pt.y, pt.z);
    }

    if (tube.name == follow) {
        let pt = tube.line_points[tube.pos_idx];
        camera.position.x = pt.x + 5000;
        camera.position.y = pt.y + 1000;
        camera.position.z = pt.z;
    }
}

function load_kill(kill_id) {

    pause = false;
    const loader = new THREE.FileLoader(loadingManager);
    if (typeof kill_id === 'undefined') {
        kill_id = -1;
    }

    console.log("Requesting kill id: " + kill_id.toString());
    loader.load("/kill_coords?kill_id=" + kill_id, function (resp) {
        var data = JSON.parse(resp);

        function animate() {

            requestAnimationFrame(animate);
            if (pause) {
                render();
            }else{

                for (var n = 0, t = tubes.length; n < t; n++) {
                    tube = tubes[n];

                    tube.drawCount += 6;
                    tube.pos_idx += 1;

                    if (tube.drawCount >= tube.draw_max) {
                        tube.drawCount = 6;
                    }

                    if (tube.pos_idx > tube.line_points.length-1) {
                        tube.pos_idx = 1;
                    }

                    tube.ribbon.geometry.setDrawRange(0, tube.drawCount);

                    tube.sphere.position.set(
                        tube.line_points[tube.pos_idx].x,
                        tube.line_points[tube.pos_idx].y,
                        tube.line_points[tube.pos_idx].z
                    );

                    set_camera(tube, look, follow);
                }

                render();
            }
        }

        function render() {
            renderer.render(scene, camera);
        }
        window.addEventListener('resize', onWindowResize, false);
        renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
        var dim = get_window_size();

        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setSize(dim.width, dim.height);
        var page = document.getElementById('killcam_div');
        var canv = document.createElement('div');
        canv.setAttribute('id', 'killcam_canv');
        page.appendChild(canv);
        canv.appendChild(renderer.domElement);

        var info = document.createElement('div');
        info.setAttribute("id", "killcam_info");
        info.style.position = 'absolute';
        info.style.top = '65px';
        info.style.width = '100%';
        info.style.textAlign = 'left';
        info.style.color = 'white';
        info.style.fontWeight = 'bold';
        info.style.backgroundColor = '#2c2d44';
        info.style.zIndex = '1';
        info.style.fontFamily = 'Monospace';
        info.innerHTML =
            "[Kill-ID: " + data.impact_id +
            "] -- [Pilot: " + data.pilot_name +
            "] -- [Weapon: " + data.weapon_name +
            "] -- [Target: " + data.target_name +
            "]";
        page.appendChild(info);

        scene = new THREE.Scene();
        scene.background = new THREE.Color('white');
        // scene.background = new THREE.MeshLambertMaterial({
            // emissive: 'white'
        // });
        var max_fog = 100000 - 3000;
        scene.fog = new THREE.Fog('white', 0.0, max_fog);

        var ambientlight = new THREE.AmbientLight(0xffffff, 10000);
        scene.add(ambientlight);

        max_pt = Math.max(data.killer.data.length, data.target.data.length, data.weapon.data.length) * 3;
        var killer = tube_prep(data.killer.data, 0x0000ff, 0, 'killer', max_pt);
        tubes.push(killer);

        var weapon = tube_prep(data.weapon.data, 'green', 0, 'weapon', max_pt);
        tubes.push(weapon);

        var target = tube_prep(data.target.data, 0xff0000, 0, 'target', max_pt);
        tubes.push(target);

        make_circle_floor(target);
        makeCameraAndControls();

        clock = new THREE.Clock();
        min_ts = data.min_ts;
        delta = data.min_ts;
        restart = 0;

        render();
        animate();
    });

    onWindowResize();
}

function stat() {
    var script = document.createElement('script');
    script.onload = function () {
        var stats = new Stats();
        document.getElementById('killcam_div').appendChild(stats.dom);
        // document.body.appendChild(stats.dom);
        requestAnimationFrame(function loop() {
            stats.update();
            requestAnimationFrame(loop);
        });
    };
    script.src = '//mrdoob.github.io/stats.js/build/stats.min.js';

    document.head.appendChild(script);
}