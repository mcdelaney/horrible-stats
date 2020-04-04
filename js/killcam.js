/*jshint esversion: 6 */
import * as THREE from "three";
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { Water } from 'three/examples/jsm/objects/Water.js';
import { Sky } from 'three/examples/jsm/objects/Sky.js';
import { GUI } from 'three/examples/jsm/libs/dat.gui.module.js';


var renderer, scene, camera, anim_id, clock, progress, light, water, sky, zoom;
var tubes = {
    killer: null,
    weapon: null,
    target: null,
    // other: null
};

window.tubes = tubes;
window.speed_mult = 3;
window.cam = camera;
window.light = light;

var pause = false;
var look = "target";
var follow = 'killer';

var POINT_MULT = 3;
const loader = new THREE.FileLoader(loadingManager);

var dir = new THREE.Vector3();

var parameters = {
    distance: 200,
    inclination: 0.1732,
    azimuth: 0.4015
};


// 73432

function pauseClick(elem) {
    if (pause === false) {
        elem.className = "nav-link active";
        pause = true;
    }else{
        elem.className = "nav-link";
        pause = false;
    }
}

function make_progress_tracker(){
    progress = document.createElement('div');
    progress.setAttribute("id", "kill_progress");
    progress.style.position = 'absolute';
    progress.style.top = '75px';
    progress.opacity = '100%';
    progress.style.textAlign = 'left';
    progress.style.paddingLeft = '91%';
    progress.style.color = 'black';
    progress.style.fontWeight = 'light';
    progress.style.zIndex = '100';
    progress.style.fontFamily = 'Monospace';
    progress.innerHTML = '0%';
    return progress;
}


function make_info_pane(data){
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
        "Initiator: " + data.killer.name + "<br>" +
        'Initiator Type: ' + data.killer.type + "<br>" +
        "Weapon: " + data.weapon.name + "<br>" +
        "Target: " + data.target.name + '<br>' +
        'Target Type: ' + data.target.type + "<br>" +
        'Collision Dist: ' + data.impact_dist + "<br>";
    return info;
}


function followClick(elem) {
    var arr = ['weapon_btn', 'target_btn', 'killer_btn'];
    for (let index = 0; index < arr.length; index++) {
        var element = document.getElementById(arr[index]);
        if (element.getAttribute('value') === elem.getAttribute('value')){
            element.className = "nav-link active";
            follow = elem.getAttribute('value');
            if (follow === 'weapon') {
                look = 'target';
            }else if(follow === "killer"){
                look = 'target';
            }else{
                look = "killer";
            }
        }else{
            element.className = "nav-link";
        }
    }
}


function make_button(id, html) {
    var btn = document.createElement("a");
    btn.setAttribute('id', id);
    btn.style.border = "1px solid black";
    btn.style.marginTop = "5px";
    btn.style.marginRight = "5px";
    btn.style.paddingTop = "2px";
    btn.style.paddingBottom = "2px";
    btn.style.paddingLeft = "2px";
    btn.style.paddingRight = "2px";
    btn.style.fontSize = "12px";
    btn.style.width="55px";
    btn.style.textAlign = "center";
    btn.className = "nav-link";
    btn.innerHTML = html;
    if (id != "pause_btn"){
        btn.addEventListener ("click", function(event) {
            var targetElement = event.target || event.srcElement;
            followClick(targetElement);
        }, false);
    }
    return btn;
}


function make_buttons(){
    var navset = document.createElement('ul');
    navset.style.marginTop = "5px";
    navset.className = "nav nav-pills";
    var li =  document.createElement("li");
    li.className = "nav-item";
    navset.appendChild(li);

    var target_row = document.createElement("div");
    target_row.className = "btn-group";
    target_row.setAttribute('role', 'group');

    var target_btn = make_button('target_btn', 'Target');
    target_btn.setAttribute('value', 'target');
    target_row.appendChild(target_btn);

    var weapon_btn = make_button('weapon_btn', 'Weapon');
    weapon_btn.setAttribute('value', 'weapon');
    target_row.appendChild(weapon_btn);

    var killer_btn = make_button('killer_btn', 'Killer');
    killer_btn.className = 'nav-link active';
    killer_btn.setAttribute('value', 'killer');
    target_row.appendChild(killer_btn);

    li.appendChild(target_row);

    var pause_btn = make_button('pause_btn', 'Pause');
    pause_btn.addEventListener ("click", function(event) {
        var targetElement = event.target || event.srcElement;
        pauseClick(targetElement);
    }, false);

    li.appendChild(pause_btn);

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

function get_model_path(obj){
    var model_path;
    if (obj.cat === 'Weapon+Missile') {
        model_path = `Missile.${obj.type}.obj`;
    } else {
        var obj_name = obj.type.split("_");
        model_path = `FixedWing.${obj_name[0]}.obj`;
    }
    console.log("Requesting model: " + model_path);
    return model_path;
}

function tube_prep(data, min_ts, max_ts) {

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
        drawCount: 0,
        cat: data.cat,
        pos_idx: 0,
        type: data.type,
        object: null,
        ribbon: null,
        name: data.name,
        pitch: [],
        roll: [],
        yaw: [],
        heading: [],
        rotation: [],
        time_step: data.time_step,
        look_points: [],
        // cam_points: [],
        counter: min_ts,
        min_ts: min_ts,
        max_ts: max_ts,
    };

    if (out.cat === 'Weapon+Missile'){
        params.width = Math.round(params.width/4);
        params.obj_scale = Math.round(params.obj_scale * 1.5);
    }

    var model_path = get_model_path(out);
    var obj_mater = new THREE.MeshPhysicalMaterial({
        reflectivity: 0.75,
        metalness: 0.75, roughness: 0.25,
        color: new THREE.Color('#C1C1C1'),
        side: THREE.DoubleSide,
        // ambientIntensity: 0.2, aoMapIntensity: 1,
        // envMapIntensity:1, normalScale: 1,
    });

    var obj_loader = new OBJLoader();

    obj_loader.load(
        "static/mesh?obj_name=" + model_path,
        function (object) {
            object.traverse(function (child) {
                if (child instanceof THREE.Mesh) {
                    child.material = obj_mater;
                }
            });
            object.scale.set(params.obj_scale, params.obj_scale, params.obj_scale);
            out.object = object;
            out.object.visible = false;
            scene.add(out.object);
        }
    );

    var points = [];
    var times = [];

    for (var i = 0, l = data.coord.length; i < l; i++) {
        points.push(new THREE.Vector3(...data.coord[i]));
        times.push(new THREE.Vector2(out.time_step[i], 1));

        let roll = to_rad(data.rot[i][0]);
        let pitch = to_rad(data.rot[i][1]);
        let yaw = to_rad(data.rot[i][2]);
        out.rotation.push(new THREE.Euler(pitch, roll, yaw));
    }

    var curve = new THREE.CatmullRomCurve3(points, false);
    out.line_points = curve.getPoints(points.length*POINT_MULT);

    var time_curve = new THREE.SplineCurve(times);
    times = time_curve.getPoints(out.line_points.length-1);
    var interp_time_steps = [];
    for (let i = 0, l = times.length; i < l; i++) {
        interp_time_steps.push(times[i].x);
    }
    out.time_step = interp_time_steps;
    console.log('First time for ' + out.name + ' is ' + out.time_step[0].toString());

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

    var max_pt0 = out.line_points.length;
    var max_pt1 = max_pt0+1;
    var widthSteps = 1;

    let pts2 = curve.getPoints(out.line_points.length);

    pts2.forEach(p => {
        p.z += params.width;
    });

    var pts = out.line_points.concat(pts2);

    var ribbonGeom = new THREE.BufferGeometry().setFromPoints(pts);

    var indices = [];
    for (var iy = 0; iy < widthSteps; iy++) {
        for (var ix = 0; ix < max_pt0; ix++) {
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
        new THREE.MeshLambertMaterial({
            side: THREE.DoubleSide, color: data.color.toLowerCase(),
            emissive: data.color.toLowerCase(), emissiveIntensity: 5 })
        );


    ribbon.geometry.setDrawRange(0, out.drawCount);
    ribbon.visible = false;
    // ribbon.castShadow = false;
    // ribbon.receiveShadow = false;

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
    // var color = new THREE.Color('#c1c1c1');
    // var plane_mat = new THREE.MeshBasicMaterial({color: '#c1c1c1', transparent: false});
    var plane_mat = new THREE.MeshBasicMaterial({color: 0x595e60, wireframe: false,side: THREE.DoubleSide,
        transparent: false});
    // plane_mat.color = color;
    var plane_1 = new THREE.Mesh( plane_geo, plane_mat );
    plane_1.lookAt(new THREE.Vector3(0, 1, 0));
    plane_1.position.set(
        target.line_points[target.line_points.length - 1].x,
        0,
        target.line_points[target.line_points.length - 1].z
    );

    var wireframe = new THREE.WireframeGeometry( plane_geo );
    var wire_material = new THREE.MeshBasicMaterial({color: 'black', transparent:false});
    var lines = new THREE.LineSegments( wireframe, wire_material);
    lines.lookAt(new THREE.Vector3(0, 1, 0));
    lines.position.set(
        target.line_points[target.line_points.length - 1].x,
        0,
        target.line_points[target.line_points.length - 1].z
    );
    // var plane = new THREE.Object3D();
    // plane.add(lines);
    // plane.add(plane_1);
    // plane.lookAt(new THREE.Vector3(0, 1, 0));

    // plane.position.set(
    //     target.line_points[target.line_points.length - 1].x,
    //     0,
    //     target.line_points[target.line_points.length - 1].z
    // );
    // scene.add( plane );
    scene.add(plane_1);
    scene.add(lines);
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
    camera.fov = Math.max(5, (zoom.getAttribute('max') - zoom.value));
    var look_pos = tubes[look].object.position;
    var follow_pos = tubes[follow].object.position;
    var cam_pos;

    var angle_back = dir.subVectors( look_pos, follow_pos ).normalize();
    cam_pos = follow_pos.clone().addScaledVector(angle_back, -1000);
    cam_pos.y = Math.max(5.0, cam_pos.y);
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

}

function make_zoom_slider(){
    var container = document.createElement("div");
    container.className = "slidercontainer";
    container.style.marginTop = "5px";
    container.style.marginRight = "5px";
    container.style.paddingTop = "2px";

    var label = document.createElement("label");
    label.setAttribute('for', 'zoom_slider');
    label.style.color = 'black';
    label.style.textAlign = 'center';
    label.style.paddingRight = "5px";
    label.style.fontSize = '13';
    label.style.fontWeight = 'light';
    label.style.zIndex = '100';
    label.style.fontFamily = 'Monospace';
    label.innerHTML = "Zoom ";
    container.appendChild(label);

    zoom = document.createElement('input');
    zoom.setAttribute("type", "range");
    zoom.className = "slider";
    zoom.setAttribute('id', 'zoom_slider');
    zoom.setAttribute('value', 100); // This is actual 50/deg fov (150-100)
    zoom.setAttribute('min',10);
    zoom.setAttribute('max',  150);
    // container.appendChild(label);
    container.appendChild(zoom);
    return container;
}


function update_objects(delta){

    for (let n = 0, t = Object.keys(tubes).length; n < t; n++) {
        if (tubes[Object.keys(tubes)[n]].object === null){
            console.log('Some objects are still null!');
            return;
        }
    }

    for (var n = 0, t = Object.keys(tubes).length; n < t; n++) {
        var keyname = Object.keys(tubes)[n];
        var tube = tubes[keyname];

        tube.counter = tube.counter + delta;
        if (tube.counter > tube.max_ts){
            // tube.time_step[tube.time_step.length-1]) {
            tube.counter = tube.min_ts;
            tube.pos_idx = 0;
            tube.drawCount = 0;
            tube.object.visible = false;
            tube.ribbon.visible = false;
        }else{
            for (var i = tube.pos_idx; i < tube.time_step.length; i++) {
                var element = tube.time_step[i];
                if (element <= tube.counter) {
                    tube.pos_idx = i;
                    tube.drawCount = (i-1)*6;
                    tube.object.visible = true;
                    tube.ribbon.visible = true;
                }else{
                    break;
                }
            }
        }

        var _pt = tube.line_points[tube.pos_idx];
        var _look = tube.look_points[tube.pos_idx];
        tube.object.position.set(_pt.x,_pt.y, _pt.z);
        tube.object.lookAt(_look.x, _look.y, _look.z);
        // tube.object.setRotationFromEuler(tube.rotation[tube.pos_idx]);
        tube.ribbon.geometry.setDrawRange(0, tube.drawCount);
        if (n === 0) {
            progress.innerHTML = ((tube.pos_idx / tube.line_points.length) * 100).toFixed(1) + "%";
        }
    }
    set_camera();
}


function animate() {

    anim_id = requestAnimationFrame(animate);
    var delta = clock.getDelta();
    delta = delta*window.speed_mult;
    if (pause === false) {
        update_objects(delta);
    }else{
        set_camera();
    }
    // updateSun();
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
}


export function remove_scene() {

    cancelAnimationFrame( anim_id );

    if (scene != null) {
        scene.dispose();
        console.log('Clearing scene...');
        while (scene.children.length > 0) {
            scene.remove(scene.children[0]);
        }
        var killcam_canv = document.getElementById('killcam_canv');
        if (killcam_canv != null) {
            killcam_canv.parentNode.removeChild(killcam_canv);
        }
    }

    var prev_info = document.getElementById('killcam_info');
    if (prev_info != null) {
        prev_info.parentNode.removeChild(prev_info);
    }
    var prev_progress = document.getElementById('kill_progress');
    if (prev_progress != null) {
        prev_progress.parentNode.removeChild(prev_progress);
    }

    pause = false;
    follow = "killer";
    look = "target";
    tubes = {
        killer: null,
        weapon: null,
        target: null,
        // other: null
    };
}


export function load_kill() {

    var kill_id = window.location.href.split("#")[2];
    remove_scene();

    if (typeof kill_id === 'undefined') {
        kill_id = "-1";
    }

    console.log("Requesting kill id: " + kill_id);
    loader.load("/kill_coords?kill_id=" + kill_id, function (resp) {
        var data = JSON.parse(resp);

        var kill_id = window.location.href.split("#")[2];
        if (typeof kill_id === 'undefined') {
            console.log("Kill id is null...Setting to: " + data.impact_id );
            window.location.href = window.location.href + "#" + data.impact_id.toString();
        }

        // document.getElementById('load_spin').hidden = true;
        window.addEventListener('resize', onWindowResize, false);
        renderer = new THREE.WebGLRenderer({antialias: true, alpha: true, powerPreference: "high-performance"});
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.toneMappingExposure = 1;

        var dim = get_window_size();

        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setSize(dim.width, dim.height);
        var page = document.getElementById('killcam_div');
        var canv = document.createElement('div');
        canv.setAttribute('id', 'killcam_canv');
        page.appendChild(canv);
        canv.appendChild(renderer.domElement);

        var info = make_info_pane(data);
        canv.appendChild(info);
        var pause_btn = make_buttons();
        info.appendChild(pause_btn);
        var zoom_slider = make_zoom_slider();
        info.appendChild(zoom_slider);

        progress = make_progress_tracker();
        canv.appendChild(progress);



        scene = new THREE.Scene();
        // scene.background = new THREE.Color('white');
        var max_fog = 1250000;
        scene.fog = new THREE.Fog('white', 100000, max_fog);

        for (let idx = 0; idx < data.other.length; idx++) {
            tubes["other_" + idx.toString()] = tube_prep(data.other[idx], data.min_ts, data.max_ts);
        }
        tubes.killer = tube_prep(data.killer, data.min_ts, data.max_ts);
        tubes.target = tube_prep(data.target, data.min_ts, data.max_ts);
        tubes.weapon = tube_prep(data.weapon, data.min_ts, data.max_ts);

        light = new THREE.DirectionalLight( 0xffffff, 0.5 );

        window.light = light;
        light.castShadow = true;
        light.add(
            new THREE.Mesh(
                new THREE.SphereBufferGeometry( .5 ),
                new THREE.MeshBasicMaterial( { color: 0xffffff } )
            )
        );

        var ambient = new THREE.AmbientLight( 0x404040 ); // soft white light
        scene.add( ambient );

        scene.add( light );

        var waterGeometry = new THREE.PlaneBufferGeometry( 1500000, 1500000 );
        water = new Water(
            waterGeometry,
            {
                textureWidth: 512,
                textureHeight: 512,
                waterNormals: new THREE.TextureLoader().load( 'static/textures/waternormals.jpg', function ( texture ) {
                    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
                } ),
                alpha: 1.0,
                sunDirection: light.position.clone().normalize(),
                sunColor: 0xffffff,
                // waterColor: 0x001e0f,
                waterColor: 0x000F1E,
                distortionScale: 3.7,
                fog: scene.fog !== undefined
            }
        );
        water.rotation.x = - Math.PI / 2;
        water.position.set(
            tubes.target.line_points[tubes.target.line_points.length - 1].x, 0,
            tubes.target.line_points[tubes.target.line_points.length - 1].z);
        scene.add( water );

        var sky = new Sky();
        var uniforms = sky.material.uniforms;
        uniforms[ 'turbidity' ].value = 5;
        uniforms[ 'rayleigh' ].value = 2;
        uniforms[ 'luminance' ].value = 1.06;
        uniforms[ 'mieCoefficient' ].value = 0.004;
        uniforms[ 'mieDirectionalG' ].value = 0.5;

        var cubeCamera = new THREE.CubeCamera( 0.1, 100000, 512 );
        cubeCamera.renderTarget.texture.generateMipmaps = true;
        cubeCamera.renderTarget.texture.minFilter = THREE.LinearMipmapLinearFilter;
        scene.background = cubeCamera.renderTarget;

        function updateSun() {

            var theta = Math.PI * ( parameters.inclination - 0.5 );
            var phi = 2 * Math.PI * ( parameters.azimuth - 0.5 );

            light.position.x = parameters.distance * Math.cos( phi );
            light.position.y = parameters.distance * Math.sin( phi ) * Math.sin( theta );
            light.position.z = parameters.distance * Math.sin( phi ) * Math.cos( theta );

            sky.material.uniforms[ 'sunPosition' ].value = light.position.copy( light.position );
            water.material.uniforms[ 'sunDirection' ].value.copy( light.position ).normalize();

            cubeCamera.update( renderer, sky );

        }

        updateSun();
        // var ambientlight = new THREE.AmbientLight(0xffffff, 10000);
        // scene.add(ambientlight);

        // make_circle_floor(tubes.target);

        // var cubeCamera = new THREE.CubeCamera( 1, 100000, 128 );
        // scene.add( cubeCamera );

        // var gui = new GUI();
        // var folder = gui.addFolder( 'Sky' );
        // folder.add( parameters, 'inclination', 0, 0.5, 0.0001 ).onChange( updateSun );
        // folder.add( parameters, 'azimuth', 0, 1, 0.0001 ).onChange( updateSun );
        // folder.add( parameters, 'distance', 0, 15000, 1 ).onChange( updateSun );
        // folder.open();

        // var uniforms = water.material.uniforms;

        // var folder = gui.addFolder( 'Water' );
        // folder.add( uniforms.distortionScale, 'value', 0, 8, 0.1 ).name( 'distortionScale' );
        // folder.add( uniforms.size, 'value', 0.1, 10, 0.1 ).name( 'size' );
        // folder.add( uniforms.alpha, 'value', 0.9, 1, .001 ).name( 'alpha' );
        // folder.open();

        dim = get_window_size();
        camera = new THREE.PerspectiveCamera(50, dim.width / dim.height, 100, 150000);

        window.camera = camera;
        scene.camera = camera;

        clock = new THREE.Clock();
        stat();
        renderer.compile(scene, camera);
        document.getElementById('load_spin').hidden = true;
        animate(progress);
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


function get_window_size() {
    var width = window.innerWidth * 0.935;
    var height = window.innerHeight * 0.88;
    var dim = {
        height: height,
        width: width
    };
    return dim;
}

function to_rad(degrees) {
    var pi = Math.PI;
    return degrees * (pi / 180);
}

// export default [load_kill, remove_scene];
// export default remove_scene;