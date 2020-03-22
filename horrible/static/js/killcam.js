/*jshint esversion: 6 */

var offset = 20;
var pilot = "someone_somewhere";
var MAX_POINTS;

var renderer, scene, camera, controls, line, drawCount, killer_obj, coords, something, prog, look_at_pt;
var tubes = [];


var elem = document.getElementById('killcam_div');

// elem.appendChild(prog);



function get_window_size() {
    var rect = elem.getBoundingClientRect();
    // console.log(rect.width + " " + rect.height);
    var width = rect.width;
    var height = width * (9 / 16) * 0.9;
    var dim = {
        'height': height,
        'width': width
    };
    return dim;
}


function make_cone(position) {

    var p1 = position[position.length - 1];
    console.log(p1);
    var p2 = position[position.length - 2];
    var dir = new THREE.Vector3();
    var subdir = dir.subVectors(p1, p2).normalize();

    height = Math.abs(p2.distanceTo(p1));
    radius = 5;
    segments = 15;
    var geom = new THREE.ConeBufferGeometry(radius, height, segments);
    geom.rotateX(subdir.x);
    geom.rotateY(subdir.y);
    geom.rotateZ(subdir.z);

    var material = new THREE.MeshNormalMaterial();
    var cone = new THREE.Mesh(geom, material);
    cone.position.x = p1.x;
    cone.position.y = p1.y;
    cone.position.z = p1.z;

    return cone;
}



var params = {
    scale: 14,
    extrusionSegments: 100,
    radiusSegments: 3,
    closed: false,
    animationView: false,
    lookAhead: false,
    cameraHelper: false,
    'radius': 13,
};


function tube_prep(data, color, init_step, name, max_pt) {

    var points = [];
    // var steps = [];
    for (var i = 0, l = data.length; i < l; i++) {
        points.push(new THREE.Vector3(...data[i]));
        // steps.push(data[i][3]);
    }

    var curve = new THREE.CatmullRomCurve3(points);
    var line_points = curve.getPoints(max_pt);
    console.log(line_points.length);

    var sphere = new THREE.Mesh(
        new THREE.SphereBufferGeometry(15, 10, 10, 0, Math.PI * 2, 0, Math.PI * 2),
        new THREE.MeshLambertMaterial({emissive: color}));
        // new THREE.MeshNormalMaterial());
    sphere.updateMatrix();

    var geometry = new THREE.TubeBufferGeometry(curve, params.extrusionSegments, params.radius, 10,
        params.closed).setFromPoints(line_points);

    geometry.scale = params.scale;
    // var drawCount = 1;
    geometry.setDrawRange(0, init_step);
    geometry.normalizeNormals();

    var tube_mesh = new THREE.Mesh(geometry, new THREE.MeshLambertMaterial({emissive: color}));

    var wire_material = new THREE.MeshBasicMaterial({
        color: color,
        opacity: 0.9,
        wireframe: true,
        transparent: true
    });

    var wireframe = new THREE.Mesh(geometry, wire_material);
    tube_mesh.add(wireframe);

    var obj_3d = new THREE.Object3D();
    obj_3d.add(tube_mesh);

    val = {
        'line_points': line_points,
        'geometry': geometry,
        'obj_3d': obj_3d,
        'mesh': tube_mesh,
        'drawCount': init_step,
        'pos_idx': 5,
        'n_draw': geometry.getIndex().count - 1,
        'step_end': init_step,
        'sphere': sphere,
        'name': name
    };

    return val;
}


function makeCameraAndControls(min_bound, max_bound, look_at_pt) {

    var dim = get_window_size();
    camera = new THREE.PerspectiveCamera(45, dim.width / dim.height, 0.01, 1000000);
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.rotateSpeed = 0.05;
    controls.zoomSpeed = 0.1;
    // controls.maxPolarAngle = Math.PI / 2 - 0.009;
    controls.target = look_at_pt;
    scene.controls = controls;
    scene.camera = camera;

    controls.addEventListener("change", () => {
        if (this.renderer) this.renderer.render(this.scene, camera);
    });

    camera.position.x = min_bound.x + 5000;
    camera.position.y = max_bound.y + 1000;
    camera.position.z = min_bound.z;
    controls.update();
    camera.updateProjectionMatrix();
    camera.lookAt(look_at_pt.x, look_at_pt.y, look_at_pt.z);
    controls.update();
    camera.updateProjectionMatrix();
}


function onWindowResize() {
    var dim = get_window_size();
    console.log("Window now is width: " + dim.width + ", height: " + dim.height);
    if (camera != null) {
        camera.aspect = dim.width / dim.height;
        renderer.setSize(dim.width, dim.height);
        camera.updateProjectionMatrix();
        controls.update();
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

function load_kill(pilot, offset) {

    const loader = new THREE.FileLoader(loadingManager);

    loader.load("/kill_coords?pilot=" + pilot + "&sec_offset=" + offset.toString(), function (resp) {
        var data = JSON.parse(resp);

        function animate() {

            requestAnimationFrame(animate);
            delta = delta + clock.getDelta();

            for (var n = 0, t = tubes.length; n < t; n++) {
                tube = tubes[n];

                tube.drawCount = Math.min(tube.drawCount + 5, tube.line_points.length*5);
                tube.pos_idx = tube.pos_idx + 1;

                if (tube.drawCount >= tube.line_points.length*5) {
                    tube.drawCount = 2;
                    tube.pos_idx = 5;
                }

                tube.geometry.setDrawRange(0, tube.drawCount);
                tube.sphere.position.set(
                    tube.geometry.attributes.position.getX(tube.pos_idx),
                    tube.geometry.attributes.position.getY(tube.pos_idx),
                    tube.geometry.attributes.position.getZ(tube.pos_idx)
                );
            }

            render();
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
        info.style.top = '100px';
        info.style.width = '100%';
        info.style.textAlign = 'center';
        info.style.color = 'white';
        info.style.fontWeight = 'bold';
        info.style.backgroundColor = '#2c2d44';
        info.style.zIndex = '1';
        info.style.fontFamily = 'Monospace';
        info.innerHTML =
            "target-id: " + data.target_id +
            ", target-name: " + data.target_name +
            ", weapon-id: " + data.weapon_id.toString() +
            ", weapon-name: " + data.weapon_name +
            ", initiator-id: " + data.killer_id.toString() +
            ", initiator-name: " + data.pilot_name;
        page.appendChild(info);

        scene = new THREE.Scene();
        // scene.background = new THREE.Color(0xffffff);
        var ambientlight = new THREE.AmbientLight(0xffffff, 1000);
        scene.add(ambientlight);

        var light = new THREE.DirectionalLight(0xffffff, 1000);
        scene.add(light);

        max_pt = Math.max(data.killer.data.length, data.target.data.length, data.weapon.data.length) * 3;
        var killer = tube_prep(data.killer.data, 0x0000ff, 2, 'killer', max_pt);
        tubes.push(killer);
        scene.add(killer.obj_3d);
        scene.add(killer.sphere);

        var weapon = tube_prep(data.weapon.data, '#2c6e27', 2, 'weapon', max_pt);
        tubes.push(weapon);
        scene.add(weapon.obj_3d);
        scene.add(weapon.sphere);

        var target = tube_prep(data.target.data, 0xff0000, 2, 'target', max_pt);
        tubes.push(target);
        scene.add(target.obj_3d);
        scene.add(target.sphere);

        var plane_geo = new THREE.CircleBufferGeometry( 100000, 10 );
        var plane_mat = new THREE.MeshBasicMaterial( {color: 0xffffff, side: THREE.DoubleSide, transparent:true, opacity: 0.25} );
        var plane_1 = new THREE.Mesh( plane_geo, plane_mat );
        var plane_wire = new THREE.MeshBasicMaterial( {color: 0xffffff, wireframe: true, transparent:true, opacity:0.25 } );
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

        killer.geometry.computeBoundingBox();

        var min_bound = killer.geometry.boundingBox.min;
        var max_bound = killer.geometry.boundingBox.max;

        var box = new THREE.BoxHelper(target.obj_3d, "black");
        // scene.add(box);

        box.geometry.computeBoundingBox();
        look_at_pt = box.geometry.boundingBox.getCenter();
        box.localToWorld( look_at_pt );

        makeCameraAndControls(min_bound, max_bound, look_at_pt);

        clock = new THREE.Clock();
        min_ts = data.min_ts;
        delta = data.min_ts;
        restart = 0;
        render();
        animate();
    });

    onWindowResize();
}

// function stat() {
//     var script = document.createElement('script');
//     script.onload = function () {
//         var stats = new Stats();
//         document.body.appendChild(stats.dom);
//         requestAnimationFrame(function loop() {
//             stats.update();
//             requestAnimationFrame(loop);
//         });
//     };
//     script.src = '//mrdoob.github.io/stats.js/build/stats.min.js';
//     document.head.appendChild(script);
// }