/*jshint esversion: 6 */

var offset = 20;
var pilot = "someone_somewhere";
var coords;
var MAX_POINTS;

var renderer, scene, camera, controls;
var line;
var killer_obj;
var drawCount;
var tubes = [];
var camera;

var elem = document.getElementById('killcam_div');
var dim = get_window_size();



function get_window_size() {
    var rect = elem.getBoundingClientRect();
    var width = rect.width;
    var height= width*(9/16) * 0.9;
    var dim = {'height': height,
               'width': width};
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
    scale: 4,
    extrusionSegments: 100,
    radiusSegments: 3,
    closed: false,
    animationView: false,
    lookAhead: false,
    cameraHelper: false,
};


function tube_prep(data, color, init_step, name, max_pt) {

    var points = [];
    var steps = [];
    for (var i = 0, l = data.length; i < l; i++) {
        points.push(new THREE.Vector3(...data[i]));
        steps.push(data[i][3]);
    }

    var curve = new THREE.CatmullRomCurve3(points);
    var line_points = curve.getPoints(max_pt);

    var sphere = new THREE.Mesh(
        new THREE.SphereBufferGeometry(15, 10, 10, 0, Math.PI * 2, 0, Math.PI * 2),
        new THREE.MeshNormalMaterial());
    sphere.updateMatrix();

    var geometry = new THREE.TubeBufferGeometry(curve, params.extrusionSegments, 7, 5,
        params.closed).setFromPoints(line_points);

    var drawCount = 1;
    geometry.setDrawRange(0, drawCount);

    var tube_mesh = new THREE.Mesh(geometry, new THREE.MeshLambertMaterial());

    var wire_material = new THREE.MeshBasicMaterial({
        color: color,
        opacity: 0.4,
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
        'drawCount': drawCount,
        'pos_idx': 5,
        'n_draw': geometry.getIndex().count - 1,
        'steps': steps,
        'step_end': init_step,
        'sphere': sphere,
        'name': name
    };

    return val;
}


function makeCameraAndControls(min_bound, max_bound, look_at_pt) {

    var dim = get_window_size();
    camera = new THREE.PerspectiveCamera(45, dim.width / dim.height, 0.01, 1000000);
    // camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.01, 1000000);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.rotateSpeed = 0.025;
    controls.zoomSpeed = 0.025;
    controls.maxPolarAngle = Math.PI / 2;
    scene.controls = controls;
    scene.camera = camera;

    controls.addEventListener("change", () => {
        if (this.renderer) this.renderer.render(this.scene, camera);
    });

    camera.position.x = min_bound.x + 25000;
    camera.position.y = max_bound.y + 2000;
    camera.position.z = min_bound.z;
    controls.update();
    camera.updateProjectionMatrix();
    camera.lookAt(look_at_pt);
    camera.updateProjectionMatrix();
    controls.update();
}


function load_kill(pilot, offset) {

    document.getElementById('load_spin').hidden = false;
    // document.getElementById('killcam_div').hidden = true;
    document.getElementById('overall_container').hidden = true;

    jQuery.getJSON("/kill_coords?pilot=" + pilot + "&sec_offset=" + offset.toString(),
        function (data) {

            function onWindowResize() {
                var dim = get_window_size();
                console.log("Window now is width: " + dim.width + ", height: " + dim.height);
                camera.aspect = dim.width / dim.height;
                camera.updateProjectionMatrix();
                renderer.setSize(dim.width, dim.height);
            }

            function animate() {

                requestAnimationFrame(animate);
                delta = delta + clock.getDelta();

                for (var n = 0, t = tubes.length; n < t; n++) {
                    tube = tubes[n];
                    if (tube.step_end >= tube.steps.length) {
                        break;
                    }

                    tube.drawCount = tube.drawCount + 5;
                    tube.pos_idx = tube.pos_idx + 1;

                    if (tube.drawCount >= tube.n_draw) {
                        tube.drawCount = 0;
                        tube.pos_idx = 5;
                    }

                    tube.sphere.position.set(
                        tube.geometry.attributes.position.getX(tube.pos_idx),
                        tube.geometry.attributes.position.getY(tube.pos_idx),
                        tube.geometry.attributes.position.getZ(tube.pos_idx)
                    );

                    tube.geometry.setDrawRange(0, tube.drawCount);

                    if (tube.step_end >= (tube.steps.length - 1)) {
                        restart += 1;
                    }
                }

                if (restart == tubes.length) {
                    console.log('Restarting tubes...');
                    for (var i = 0, l = tubes.length; i < l; i++) {
                        tubes[i].step_end = 2;
                    }
                    clock = new THREE.Clock();
                    delta = min_ts;
                    restart = 0;
                }

                render();
            }

            function render() {
                renderer.render(scene, camera);
            }

            renderer = new THREE.WebGLRenderer({antialias: true, alpha: true });
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.setSize(dim.width, dim.height);
            var page = document.getElementById('killcam_div');
            var canv = document.createElement('div');
            page.appendChild(canv);
            canv.appendChild(renderer.domElement);

            var info = document.createElement('div');
            info.style.position = 'absolute';
            info.style.top = '100px';
            info.style.width = '100%';
            info.style.textAlign = 'center';
            info.style.color = 'white';
            info.style.fontWeight = 'bold';
            info.style.backgroundColor = 'transparent';
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
            // scene.background = new THREE.Color(0xf0f0f0);

            var light = new THREE.DirectionalLight(0xffffff);
            // light.position.set( target.line_points[target.line_points.length-1].x*1.2,
            //                     target.line_points[target.line_points.length-1].x*1.2,
            //                     target.line_points[target.line_points.length-1].z * 1.2 );
            scene.add( light );

            window.addEventListener('resize', onWindowResize, false);

            max_pt = Math.max(data.killer.data.length, data.target.data.length, data.weapon.data.length) * 3;
            var killer = tube_prep(data.killer.data, 0x0000ff, 2, 'killer', max_pt);
            tubes.push(killer);
            scene.add(killer.obj_3d);
            scene.add(killer.sphere);

            var weapon = tube_prep(data.weapon.data, 0x008000, 2, 'weapon', max_pt);
            tubes.push(weapon);
            scene.add(weapon.obj_3d);
            scene.add(weapon.sphere);

            var target = tube_prep(data.target.data, 0xff0000, 2, 'target', max_pt);
            tubes.push(target);
            scene.add(target.obj_3d);
            scene.add(target.sphere);

            var grid = new THREE.GridHelper(100000, 10);
            grid.color = new THREE.Color(0xf0f0f0);
            grid.position.set(
                target.line_points[target.line_points.length - 1].x, 0,
                target.line_points[target.line_points.length - 1].z);
            scene.add(grid);

            target.geometry.computeBoundingBox();
            var min_bound = target.geometry.boundingBox.min;
            var max_bound = target.geometry.boundingBox.max;

            // var box = new THREE.BoxHelper(weapon.obj_3d, "black");
            // scene.add(box);

            // var look_at_pt = target.line_points[target.line_points.length - 1];
            var look_at_pt = weapon.line_points[(Math.round(weapon.line_points.length / 2))];
            makeCameraAndControls(min_bound, max_bound, look_at_pt);

            clock = new THREE.Clock();
            min_ts = data.min_ts;
            delta = data.min_ts;
            restart = 0;

            animate();
        });
        document.getElementById('load_spin').hidden = true;
        document.getElementById('killcam_div').hidden = false;
}

function stat() {
    var script = document.createElement('script');
    script.onload = function () {
        var stats = new Stats();
        document.body.appendChild(stats.dom);
        requestAnimationFrame(function loop() {
            stats.update();
            requestAnimationFrame(loop);
        });
    };
    script.src = '//mrdoob.github.io/stats.js/build/stats.min.js';
    document.head.appendChild(script);
}

// $(document).ready(function () {
//     stat();
//     load_kill(pilot, offset);
// });
