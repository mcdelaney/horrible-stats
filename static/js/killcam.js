/*jshint esversion: 6 */

var renderer, scene, camera, controls, killer_obj, coords,time,
     something, prog, render, animate, light, max_pt, progress;
var tubes = {
    killer: null,
    weapon: null,
    target: null,
    // other: null
};

var pause = false;
var elem = document.getElementById('killcam_div');
var look = "weapon";
var follow = 'killer';
var CONTROLS = false;

var POINT_MULT = 3;
var dir = new THREE.Vector3();
// 73432


function pauseClick() {
    var elem = document.getElementById('pause_btn');
    if (pause === false) {
        elem.innerHTML = "Play";
        pause = true;
    }else{
        elem.innerHTML = "Pause";
        pause = false;
    }
}

function make_button(){
    var btn = document.createElement("a");
    btn.setAttribute('id', 'pause_btn');
    btn.style.border = "2px solid black";
    btn.style.paddingTop = "2px";
    btn.style.paddingBottom = "2px";
    btn.style.paddingLeft = "2px";
    btn.style.paddingRight = "2px";
    btn.style.fontSize = "12px";
    btn.style.width="55px";
    btn.style.textAlign = "center";

    btn.className = "nav-link";
    btn.innerHTML = "Pause";
    btn.setAttribute('onclick',  'pauseClick()');

    var li =  document.createElement("li");
    li.className = "nav-item";
    li.appendChild(btn);

    var navset = document.createElement('ul');
    navset.style.marginTop = "5px";
    navset.className = "nav nav-pills";
    navset.appendChild(li);
    return navset;
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

function tube_prep(data, color, name, max_pt) {

    var params = {
        width: 15,
        obj_scale: 8,
        animationView: false,
        lookAhead: false,
        cameraHelper: false,
        radius: 10,
        opacity: 0.7,
    };

    var out = {
        line_points: null,
        draw_max: null,
        drawCount: 6,
        pos_idx: 0,
        object: null,
        ribbon: null,
        name: name,
        pitch: [],
        roll: [],
        yaw: [],
        heading: [],
        rotation: [],
        time_step: [],
        look_points: [],
        cam_points: [],
    };

    if (name === 'weapon'){
        params.width = Math.round(params.width/4);
        params.opacity = 1.0;
    }

    var model_path = get_model_path(out.name);

    var obj_mater = new THREE.MeshStandardMaterial({'color': color});
    var obj_loader = new THREE.OBJLoader();
    obj_loader.load(
        model_path,
        onLoad = function (object) {
            object.traverse(function (child) {
                if (child instanceof THREE.Mesh) {
                    child.material = obj_mater;
                }
            });

            object.scale.x = params.obj_scale;
            object.scale.y = params.obj_scale;
            object.scale.z = params.obj_scale;
            // object.position.set(out.line_points[0].x, out.line_points[0].y, out.line_points[0].z);
            out.object = object;
            scene.add(out.object);
        }
    );


    var points = [];
    var dup = Math.ceil(max_pt / data.length) + 1;
    for (var i = 0, l = data.length; i < l; i++) {
        // points.push(new THREE.Vector3(...calcPosFromLatLonRad(data[i][0], data[i][1], data[i][2])));
        let pt = new THREE.Vector3(data[i][0], data[i][1], data[i][2]);
        points.push(pt);

        for (var n = 0, w = dup; n < w; n++) {
            let pitch = to_rad(data[i][4]);
            let roll = to_rad(data[i][3]);
            let yaw = to_rad(data[i][5]);
            out.rotation.push(new THREE.Euler(pitch, roll, yaw));
            out.pitch.push(pitch);
            out.roll.push(roll);
            out.yaw.push(yaw);
            out.heading.push(to_rad(data[i][6]));
            out.time_step.push(to_rad(data[i][7]));
        }
    }

    var curve = new THREE.CatmullRomCurve3(points, false);
    out.line_points = curve.getPoints(max_pt);

    // var dir = new THREE.Vector3(); // create once an reuse it
    for (let i = 0, l=out.line_points.length; i < l; i++) {

        if (i >= out.line_points.length-1) {
            out.look_points.push(out.look_points[i-1].clone());
        }else{
            var angle_forw = dir.subVectors( out.line_points[i], out.line_points[i+1] ).normalize();
            var dist_pt_forw = out.line_points[i].clone().addScaledVector(angle_forw, 10);
            out.look_points.push(dist_pt_forw);
        }
    }

    for (let i = 1, l=out.line_points.length; i <= l; i++) {
        if (i === out.line_points.length) {
            out.cam_points.splice(0, 0, out.cam_points[0].clone());
        }else{
            var angle_back = dir.subVectors( out.line_points[i], out.line_points[i-1] ).normalize();
            var dist_pt_back = out.line_points[i].clone().addScaledVector(angle_back, -1000);
            out.cam_points.push(dist_pt_back);
        }
    }

    var max_pt1 = max_pt+1;
    var widthSteps = 1;
    let pts2 = curve.getPoints(max_pt);
    pts2.forEach(p => {
        p.z += params.width;
    });

    var pts = out.line_points.concat(pts2);

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

    var ribbon = new THREE.Mesh(ribbonGeom,
        new THREE.MeshLambertMaterial({side: THREE.DoubleSide, color: color,
                                       emissive: color, emissiveIntensity: 5,
                                       transparent: true, opacity: params.opacity})
        );

    ribbon.geometry.setDrawRange(0, out.drawCount);
    scene.add(ribbon);
    out.ribbon = ribbon;

    out.draw_max = out.line_points.length*3*2;

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


function make_circle_floor(target){
    var plane_geo = new THREE.CircleBufferGeometry( 150000, 10 );
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

function set_camera(){
    // 62682
    var look_pos = tubes[look].object.position;
    var follow_pos = tubes[follow].object.position;
    var obj_dist =  Math.abs(follow_pos.distanceTo(look_pos));
    var cam_pos;

    // console.debug("OBject dist: " + obj_dist.toString());
    // cam_pos = tubes[follow].cam_points[tubes[follow][tubes[follow].pos_idx]];
    // look_pos = tubes[follow].look_points[tubes[follow][tubes[follow].pos_idx]];

    var angle_back = dir.subVectors( look_pos, follow_pos ).normalize();
    cam_pos = follow_pos.clone().addScaledVector(angle_back, -1000);
    look_pos = follow_pos.clone().addScaledVector(angle_back, 200);

    try {
        camera.position.set(cam_pos.x, cam_pos.y, cam_pos.z);
        camera.translateY(200);
    } catch(error){
        console.debug(error);
        console.debug('No cam position');
    }
    try {
        camera.lookAt(look_pos.x, look_pos.y, look_pos.z);
    } catch (error) {
        console.debug(error);
        console.debug('No look pos');
    }



    if (CONTROLS === true) {
        controls.update();
    }
}

function make_zoom_slider(){
    var container = document.createElement("div");
    // container.className = "slidecontainer";
    var input = document.createElement('input');
    input.setAttribute("type", " range");
    input.className = "custom-range";
    input.setAttribute('id', 'zoom_slider');
    input.setAttribute('value', 5);
    input.setAttribute('min', 1);
    input.setAttribute('max', '10');
    container.appendChild(input);
    container.style.width = '80px';
    return container;
}

function update_objects(){
    if (tubes.killer.object === null | tubes.target.object === null | tubes.weapon.object === null) {
        console.log('Some objects are still null!');
        return;
    }else{

        for (var n = 0, t = Object.keys(tubes).length; n < t; n++) {
            var keyname = Object.keys(tubes)[n];
            tube = tubes[keyname];
            if (tube === null) {
                continue;
            }

            var _pt = tube.line_points[tube.pos_idx];
            var _look = tube.look_points[tube.pos_idx];

            if (tube.object != null ){
                tube.object.position.set(_pt.x,_pt.y, _pt.z);
                tube.object.lookAt(_look.x, _look.y, _look.z);
                // tube.object.setRotationFromEuler(tube.rotation[tube.pos_idx]);
                tube.ribbon.geometry.setDrawRange(0, tube.drawCount);
            }
            // tube.ribbon.geometry.computeVertexNormals();
            // tube.ribbon.rojectionMatrix()

            if (n === 0) {
                progress.innerHTML = Math.round((tube.pos_idx / max_pt) * 100).toString() + "%";
            }

            tube.drawCount += 6;
            tube.pos_idx += 1;

            if (tube.drawCount >= tube.draw_max) {
                tube.drawCount = 6;
            }

            if (tube.pos_idx >= tube.line_points.length - 1) {
                tube.pos_idx = 0;
            }
        }
        set_camera();
    }
}


function animate() {

    requestAnimationFrame(animate);
    if (pause === false) {
        update_objects();
    }
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
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
        info.style.fontSize = '13';
        info.style.fontWeight = 'light';
        info.style.zIndex = '100';
        info.style.fontFamily = 'Monospace';
        info.innerHTML =
            "Kill-ID: " + data.impact_id + "<br>" +
            "Initiator: " + data.killer_name + "<br>" +
            'Initiator Type: ' + data.killer_type + "<br>" +
            "Weapon: " + data.weapon_name + "<br>" +
            "Target: " + data.target_name + '<br>' +
            'Target Type: ' + data.target_type + "<br>" +
            'Collision Dist: ' + data.impact_dist + "<br>";

        var pause_btn = make_button();
        info.appendChild(pause_btn);
        // var zoom_slider = make_zoom_slider();
        // info.appendChild(zoom_slider);
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

        var max_fog = 125000;
        scene.fog = new THREE.Fog('white', 0.0, max_fog);

        var ambientlight = new THREE.AmbientLight(0xffffff, 10000);
        scene.add(ambientlight);

        max_pt = Math.max(data.killer.data.length, data.target.data.length, data.weapon.data.length) * POINT_MULT;
        tubes.killer = tube_prep(data.killer.data, 0x0000ff, 'killer', max_pt);
        tubes.weapon = tube_prep(data.weapon.data, 'black', 'weapon', max_pt);
        tubes.target = tube_prep(data.target.data, 0xff0000, 'target', max_pt);

        make_circle_floor(tubes.target);
        makeCameraAndControls(add_controls=CONTROLS);
        // camera.position.set(tubes.killer.cam_points[0].x, tubes.killer.cam_points[0].y,
        //     tubes.killer.cam_points[0].z);
        // // camera.lookAt(tubes.killer.look_points[0].x, tubes.killer.look_points[0].y,
        // //         tubes.killer.look_points[0].z);
        // camera.updateProjectionMatrix();

        clock = new THREE.Clock();
        min_ts = data.min_ts;
        delta = data.min_ts;
        restart = 0;
        // stat();
        renderer.compile(scene, camera);
        animate();
    });

    onWindowResize();
}

function stat() {
    var script = document.createElement('script');
    script.onload = function () {
        var stats = new Stats();
        document.getElementById('killcam_info').appendChild(stats.dom);
        requestAnimationFrame(function loop() {
            stats.update();
            requestAnimationFrame(loop);
        });
    };
    script.src = '//mrdoob.github.io/stats.js/build/stats.min.js';
    document.head.appendChild(script);
}


$(document).onkeypress = function (e) {
    e = e || window.event;
    console.log(e);
    if (paused === true) {
        paused = false;
    }else{
        paused = true;
    }
};
