/*jshint esversion: 6 */
import $ from 'jquery';
import 'datatables.net';
// import 'datatables.net-bs4';

import {moment} from "moment";
import {load_kill, remove_scene} from "./killcam";

var sortKeys = {
    "overall": [
        [2, "desc"]
    ],
    "session_performance": [],
    "stat_logs": [
        [1, "desc"]
    ],
    "event_logs": [
        [1, "desc"]
    ],
    "weapon_db": [],
    "tacview": [
        [1, "desc"]
    ],
    "events": [
        [0, "desc"]
    ],
    "weapons": [3, 'desc'],
    "losses": [
        [2, "desc"]
    ],
    "kills": [
        [3, "desc"]
    ],
    "frametime_logs": [
        [1, "desc"]
    ],
    "tacview_kills": [
        [0, "desc"]
    ]
};


function load_chart(path, pctile) {
    console.log("Loading chart for: " + path);
    var timeFormat = "YYYY-MM-DD HH:mm:ss";
    var chart_nm = path + "_chart";
    $.getJSON("/" + path + "?pctile=" + pctile,
        function (data) {

            var ctx = document.getElementById(chart_nm).getContext('2d');
            var chart = new Chart(ctx, {
                type: 'line',
                // labels: ['Percentile 10 FPS'],
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.data,
                        label: 'Percentile 10 FPS'
                    }],
                },
                options: {
                    // showLine: true,
                    scales: {
                        xAxes: [{
                            type: 'time',
                            time: {
                                parser: timeFormat,
                                unit: 'second',
                                // round: 'day'
                                tooltipFormat: 'YYYY-MM-DD HH:mm:ss',
                                // displayFormats: {
                                //   second: 'h:mm:ss a',
                                //     minute: 'HH:mm',
                                //     hour: 'HH'
                                // }
                            }
                            // display: true,
                            // scaleLabel: {
                            //     display: true,
                            //     labelString: 'Time'
                            // }
                        }]

                        //       xAxes: [{
                        //         type: 'time',
                        //         scaleLabel: {
                        //                   display:     true,
                        //                   labelString: 'Date'
                        //               },
                        //         time:       {
                        //           unit: 'second',
                        //           parser: timeFormat,
                        //           tooltipFormat: 'll'
                        //         },
                        //       }]
                    }
                }
            });

        });
}

/** 
*   SW: loads data tables
*   @param {*} path
*/

function load_dt(path) {

    console.log("Loading table: " + path);
    var tbl_nm = "#overall_tbl";

    document.getElementById('killcam_div').hidden = true;
    document.getElementById('load_spin').hidden = false;

    try {
        if ($.fn.dataTable.isDataTable(tbl_nm)) {
            $(tbl_nm).DataTable().destroy();
            $(tbl_nm).empty();
        }
    } catch (e) {
        console.log(e.stack);
    }

    $.getJSON("/" + path, function (data) {

        var cols = [];
        for (var i = 0; i < data.columns.length; i++) {
            var col_nm = data.columns[i].split("_");
            for (var n = 0; n < col_nm.length; n++) {
                col_nm[n] = col_nm[n].charAt(0).toUpperCase() + col_nm[n].slice(1);
            }
            col_nm = {
                "title": col_nm.join(" ")
            };
            if (col_nm.title === 'Session Date') {
                col_nm.render = function (data, type) { // jshint ignore:line
                    return type === 'sort' ? data : moment(data).format('L');
                };
            }
            cols.push(col_nm);
        }

        $(tbl_nm).DataTable({
            data: data.data,
            columns: cols,
            order: sortKeys[path],
            paging: false,
            pageLength: 50,
            rowId: "index",
            fixedColumns: false,
            autoWidth: true,
            // lengthChange: false,
            // width:"1200px",
            scrollY: 600,
            info: false,
            scrollX: true,
            // sScrollX: "100%",
        });

        document.getElementById('load_spin').hidden = true;
        document.getElementById('overall_container').hidden = false;
        $(tbl_nm).DataTable().columns.adjust();
    });
}


function set_click_attr (){
    var navs = document.getElementById('nav_set');
    for (let index = 0; index < navs.children.length; index++) {
        var btn = navs.children[index].children[0];
        btn.addEventListener ("click", function(event) {
            var targetElement = event.target || event.srcElement;
            set_onclick(targetElement);
        }, false);
    }
}


function set_onclick(elem, kill_id) {
    set_tab_active(elem.id);
//show killcam
    if (elem.id === "killcam") {
        console.log('Killcam render starting...');
        document.getElementById('load_spin').hidden = false;
        document.getElementById('overall_container').hidden = true;
        document.getElementById('killcam_div').hidden = false;
        if (typeof kill_id != 'undefined') {
            window.location.href += "#" + kill_id;
        }
        load_kill();
        //else load table with elem.id
    } else {
        remove_scene();
        load_dt(elem.id);
    }

//    if (elem.id === "maps") {
//        console.log('Loading maps...');
 //       onclick_maps();
 //   }
}

function onclick_maps() {
    // "/mapping"
    $.ajax({
        url: '/maps',
        type: "GET",
        data: JSON.stringify(request),
        processData: false,
        contentType: 'application/json'
    });

    downloadURI("data:text/html, MapFile", "./map.html");
    window.open("/map.html");
    //window.location.href = "horrible/maps/map.html";

}

/** SW: Sets active table via button click */
function set_tab_active(elem_id) {
    window.location.href = "#" + elem_id; // e.g. #overall
    var btnContainer = document.getElementById("nav_set");
    // Get all buttons with class="btn" inside the container
    var btns = btnContainer.getElementsByClassName("nav-link");
    // Loop through the buttons and add the active class to the current/clicked button
    for (var i = 0; i < btns.length; i++) {
        // console.log('Checking btn: ' + btns[i].id + " with path: " + path);
        if (elem_id === btns[i].id) {
            btns[i].className = "nav-link active";
        }else{
            btns[i].className = "nav-link";
        }
    }
}

/** 
*   SW: Download a file
*   @param {*} uri e.g. "data:text/html,HelloWorld!" @param {*} name - filename
*/

function downloadURI(uri, name) {
    var link = document.createElement("a");
    link.download = name;
    link.href = uri;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    //delete link;
  }

/** 
*   SW: Test function to popup download dialog
*   @param {*} tv_filename string/any
*/
function get_tacview_file(filename){

    var userPreference;

    var fields = filename.split(','); //get everything before "XXX.acmi", <--comma
    var tv_filename = fields[0]; // /tacview/filename.acmi


    if (confirm(`Do you want to download file? ${tv_filename}`) == true) {
        userPreference = 1;
        
        function on_request_success(response) {
            console.debug('response', response);
        } 

        function on_request_error(r, text_status, error_thrown) {
            console.debug('error', text_status + ", " + error_thrown + ":\n" + r.responseText);
        }

        var request = {tv_filename};
        
        $.ajax({
            url: '/get_tacview_file?filename=' + tv_filename,
            type: "GET",
            data: JSON.stringify(request),
            processData: false,
            contentType: 'application/json'
        });

        //var local_filename = "horrible/" + tv_filename // "horrible/tacview/filename.acmi"
        fields = tv_filename.split('/');
        tv_filename = fields[1]; // /tacview/filename.acmi


        //downloadURI("data:text/html,HelloWorld!", "helloWorld.txt");
        downloadURI("data:text/html, TacviewAcmi", tv_filename);
        //downloadURI("data:application/zip", tv_filename);

    } else {
        userPreference = -1;
        // do nothing
    }
}

$(document).ready(function () {
    set_click_attr();
    var param = window.location.href.split("#");
    if (param.length === 1) {
        let elem = document.getElementById("overall");
        set_onclick(elem);
    }else{
        let elem = document.getElementById(param[1]);
        set_onclick(elem, param[2]);
    }
});

// here is defined VAR selected_row. data for the row clicked on
$('#overall_tbl').on('click', 'tbody tr', function () {
    var current = document.getElementsByClassName("active"); //current active element

    var table = $('#overall_tbl').DataTable(); // the table
    var selected_row = table.row(this).data(); // all the selected row data
    var tac_filename = selected_row;

//  SW
    if (current[0].id == 'tacview') {
        var endpoint = 'process_tacview?filename='; // SW: whats this?
        var row_id = 0;

        selected_row.onclick(get_tacview_file(String(tac_filename))); // SW: Send to function to trigger popup

    }else if (current[0].id == 'tacview_kills') {
        var kill_id = selected_row[selected_row.length - 1].toString();
        console.log(kill_id);
        window.location.href = '#killcam';
        var elem = document.getElementById('killcam');
        set_onclick(elem, kill_id);
        return;

    }else if (current[0].id == 'maps') {
        console.log('Loading maps...');
        window.location.href = '#maps';
        onclick_maps();
        //window.open("/static/maps/map.html");
        return;

    }else {
        return;
    }

// SW this handles the database request for the Tvw Files?
    $.ajax({
        // data: data[0],
        url: "/process_tacview?filename=" + selected_row[0],
        beforeSend: function(){
            console.log('Sending request to process file: ' + selected_row[0]);
        },
        success: function (response) {
            console.log(response);
        },
        error: function(response){
            console.log(response);
        }
    });

});

