/*jshint esversion: 6 */
var renderer, scene, camera, controls, line, drawCount, killer_obj, coords,time,
     something, prog, look_at_pt, render, animate, light, max_pt, progress;
var tubes = [];
var pause = false;
var elem = document.getElementById('killcam_div');
var look = "weapon";
var follow = 'killer';
var CONTROLS = false;
var obj_loader = new THREE.OBJLoader(loadingManager);


function get_window_size() {
    var width = window.innerWidth * 0.935;
    var height = window.innerHeight * 0.88;
    var dim = {
        height: height,
        width: width
    };
    return dim;
}


function ToQuaternion(yaw, pitch, roll) // yaw (Z), pitch (Y), roll (X)
{
    // Abbreviations for the various angular functions
    cy = Math.cos(yaw * 0.5);
    sy = Math.sin(yaw * 0.5);
    cp = Math.cos(pitch * 0.5);
    sp = Math.sin(pitch * 0.5);
    cr = Math.cos(roll * 0.5);
    sr = Math.sin(roll * 0.5);

    w = cy * cp * cr + sy * sp * sr;
    x = cy * cp * sr - sy * sp * cr;
    y = sy * cp * sr + cy * sp * cr;
    z = sy * cp * cr - cy * sp * sr;

    return [x, y, z, w];
}

var params = {
    width: 20,
    obj_scale: 8,
    animationView: false,
    lookAhead: false,
    cameraHelper: false,
    radius: 10,
};


function to_rad(degrees) {
    var pi = Math.PI;
    return degrees * (pi / 180);
}


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

function get_model_path(obj_name){
    var model_path;
    if (obj_name === 'weapon') {
        model_path = '/static/mesh/Missile.AIM-120C.obj';
    } else {
        model_path = '/static/mesh/FixedWing.F-18C.obj';
    }
    return model_path;
}

function tube_prep(data, color, init_step, name, max_pt) {

    var out = {
        line_points: null,
        draw_max: null,
        drawCount: init_step,
        pos_idx: 0,
        object: null,
        ribbon: null,
        tween: null,
        name: name,
        angles: null
    };

    var points = [];
    var angles = [];
    for (var i = 0, l = data.length; i < l; i++) {
        // points.push(new THREE.Vector3(...calcPosFromLatLonRad(data[i][0], data[i][1], data[i][2])));
        points.push(new THREE.Vector3(data[i][0], data[i][1], data[i][2]));
        angles.push(new THREE.Euler(to_rad(data[i][3]), to_rad(data[i][4]), to_rad(data[i][5])));
    }
    out.angles = angles;

    var curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.05);
    var line_points = curve.getPoints(max_pt);

    var max_pt1 = max_pt+1;
    var widthSteps = 1;
    let pts2 = curve.getPoints(max_pt);
    pts2.forEach(p => {
        p.z += params.width;
    });

    var pts = line_points.concat(pts2);

    var ribbonGeom = new THREE.BufferGeometry().setFromPoints(pts);

    var indices = [];
    for (iy = 0; iy < widthSteps; iy++) {
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
    out.ribbon = ribbon;

    var model_path = get_model_path(out.name);

    var obj_mater = new THREE.MeshStandardMaterial({'color': color});
    obj_loader.load(
        model_path,
        success = function (object) {
            object.traverse(function (child) {
                if (child instanceof THREE.Mesh) {
                    child.material = obj_mater;
                }
            });

            object.scale.x = params.obj_scale;
            object.scale.y = params.obj_scale;
            object.scale.z = params.obj_scale;

            object.position.set(line_points[0].x, points[0].y, points[0].z);
            object.setRotationFromEuler(angles[0]);
            // object.computeVertexNormals();
            // object.normalizeNormals();
            out.object = object;
            scene.add(out.object);
            // out.tween = make_tween_chain(data, 'black', 'target', object);
        }
    );

    // var object = new THREE.Mesh(
    //     new THREE.objectBufferGeometry(15, 10, 10, 0, Math.PI * 2, 0, Math.PI * 2),
    //     new THREE.MeshBasicMaterial({color: color}));
    // object.updateMatrix();
    // scene.add(object);
    // out.object = object;

    out.line_points = line_points;
    out.draw_max = line_points.length*3*2;

    return out;
}


function calcPosFromLatLonRad(lat, lon, radius) {

    var phi = (90 - lat) * (Math.PI / 180);
    var theta = (lon + 180) * (Math.PI / 180);

    x = -((radius) * Math.sin(phi) * Math.cos(theta));
    z = ((radius) * Math.sin(phi) * Math.sin(theta));
    y = ((radius) * Math.cos(phi));

    return [x, y, z];
}


function make_tween_chain(data, color, name, object) {
    var points = [];
    var times = [];
    for (var i = 0, l = data.length; i < l; i++) {
        points.push(new THREE.Vector3(...data[i]));

        if (i === 0){
            times.push(0);
        }else{
            times.push((data[i][3] - data[i-1][3])*1000);
        }
    }

    // var object = new THREE.Mesh(
    //     new THREE.SphereBufferGeometry(15, 10, 10, 0, Math.PI * 2, 0, Math.PI * 2),
    //     new THREE.MeshBasicMaterial({
    //         color: 'black'
    //     }));

    object.position.set(points[0].x, points[0].y, points[0].z);
    scene.add(object);
    object.updateMatrix();

    var firstTween = new TWEEN.Tween(object);
    var earlierTween = firstTween;
    for (var i = 0, l = points.length; i < l; i++) {
        var tween = new TWEEN.Tween(object);
        tween.to({x: points[i].x, y: points[i].y, z: points[i].z}, times[i]);
        earlierTween.chain(tween);
        earlierTween = tween;
    }
    firstTween.start();
    return earlierTween;
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


function makeCameraAndControls(add_controls) {
    var dim = get_window_size();
    camera = new THREE.PerspectiveCamera(55, dim.width / dim.height, 0.01, 1000000);

    if (add_controls) {
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.07;
        controls.rotateSpeed = 0.05;
        controls.zoomSpeed = 0.05;
        // controls.maxPolarAngle = Math.PI / 2 - 0.009;
        scene.controls = controls;
        controls.addEventListener("change", () => {
            if (this.renderer) this.renderer.render(this.scene, camera);
        });
    }
    scene.camera = camera;
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
        let pt = tube.object.position;
        camera.position.x = pt.x + 3000;
        camera.position.y = pt.y + 1000;
        camera.position.z = pt.z;
    }
    // camera.updateProjectionMatrix();
    // controls.update();
}

function animate(time) {

    requestAnimationFrame(animate);
    if (pause) {
        camera.updateProjectionMatrix();
        renderer.render(scene, camera);
    } else {

        for (var n = 0, t = tubes.length; n < t; n++) {
            tube = tubes[n];

            tube.drawCount += 6;
            tube.pos_idx += 1;

            if (tube.drawCount >= tube.draw_max) {
                tube.drawCount = 6;
            }

            if (tube.pos_idx > tube.line_points.length - 1) {
                tube.pos_idx = 1;
            }

            var pnow = tube.line_points[tube.pos_idx];
            tube.ribbon.geometry.setDrawRange(0, tube.drawCount);
            tube.object.position.set(pnow.x, pnow.y, pnow.z);
            // tube.object.updateProjectionMatrix();
            // tube.object.setRotationFromEuler(tube.angles[tube.pos_idx]);

            set_camera(tube, look, follow);

            if (n === 0) {
                progress.innerHTML = Math.round((tube.pos_idx / max_pt) * 100).toString() + "%";
            }

        }

        renderer.render(scene, camera);
    }
}

function load_kill(kill_id) {

    pause = false;
    const loader = new THREE.FileLoader(loadingManager);
    if (typeof kill_id === 'undefined') {
        kill_id = -1;
    }
    // kill_id = 14;
    console.log("Requesting kill id: " + kill_id.toString());
    loader.load("/kill_coords?kill_id=" + kill_id, function (resp) {
        var data = JSON.parse(resp);



        // function render() {
        //     renderer.render(scene, camera);
        // }
        document.getElementById('load_spin').hidden = true;
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
        info.style.top = '75px';
        info.opacity = '100%';
        info.style.textAlign = 'left';
        info.style.paddingLeft= '5px';
        info.style.color = 'black';
        info.style.fontWeight = 'light';
        info.style.zIndex = '100';
        info.style.fontFamily = 'Monospace';
        info.innerHTML =
            "Kill-ID: " + data.impact_id + "<br>" +
            "Initiator: " + data.killer_name + "<br>" +
            'Initiator Type: ' + data.killer_type + "<br>" +
            "Weapon: " + data.weapon_name + "<br>" +
            "Target: " + data.target_name + '<br>' +
            'Target Type: ' + data.target_type + "<br>";
        canv.appendChild(info);

        progress = document.createElement('div');
        progress.setAttribute("id", "kill_progress");
        progress.style.position = 'absolute';
        progress.style.top = '75px';
        progress.opacity = '100%';
        progress.style.textAlign = 'right';
        progress.style.paddingLeft = '92%';
        progress.style.color = 'black';
        progress.style.fontWeight = 'light';
        progress.style.zIndex = '100';
        progress.style.fontFamily = 'Monospace';
        progress.innerHTML = '0%';
        canv.appendChild(progress);

        scene = new THREE.Scene();
        scene.background = new THREE.Color('white');

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
        makeCameraAndControls(add_controls=CONTROLS);

        clock = new THREE.Clock();
        min_ts = data.min_ts;
        delta = data.min_ts;
        restart = 0;
        stat();
        renderer.render(scene, camera);
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
            // stats.update();
            requestAnimationFrame(loop);
        });
    };
    script.src = '//mrdoob.github.io/stats.js/build/stats.min.js';

    document.head.appendChild(script);
}