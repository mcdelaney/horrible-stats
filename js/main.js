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
    "session_performance": [
        0, "desc"
    ],
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




function load_dt(path) {

    console.log("Loading table: " + path);
    var tbl_nm = "#overall_tbl";

    document.getElementById('killcam_div').hidden = true;
    document.getElementById('load_spin').hidden = false;

    $.getJSON("/" + path, function (data) {

        try {
            if ($.fn.dataTable.isDataTable(tbl_nm)) {
                $(tbl_nm).DataTable().destroy();
                $(tbl_nm).empty();
            }
        }catch (err) {
            console.log(err)
        }

        var tbl = $(tbl_nm).DataTable({
            data: data.data,
            columns: data.columns,
            order: sortKeys[path],
            paging: false,
            pageLength: 50,
            rowId: "index",
            fixedColumns: false,
            autoWidth: true,
            scrollY: 600,
            info: false,
            scrollX: true,
            initComplete: function() {
                
                this.api().columns.adjust();

                document.getElementById('load_spin').hidden = true;
                document.getElementById('overall_container').hidden = false;
            }
        });
        
        
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

    if (elem.id === "killcam") {
        console.log('Killcam render starting...');
        document.getElementById('load_spin').hidden = false;
        document.getElementById('overall_container').hidden = true;
        document.getElementById('killcam_div').hidden = false;
        if (typeof kill_id != 'undefined') {
            window.location.href += "#" + kill_id;
        }
        load_kill();
    } else {
        remove_scene();
        load_dt(elem.id);
    }
}

function set_tab_active(elem_id) {
    window.location.href = "#" + elem_id;
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


// //SW: function get_tacview_file(elem,filename){
// // Test popup for onclick of TVw table
// function get_tacview_file(tv_filename){

//     var userPreference;

//     if (confirm(`Do you want to download file? ${tv_filename}`) == true) {
//         userPreference = 1;
//         //get file
//     } else {
//         userPreference = -1;
//         // do nothing
//     }
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

// var selected_row;
$('#overall_tbl').on('click', 'tbody tr', function () {
    var current = document.getElementsByClassName("active"); //current active element

    var table = $('#overall_tbl').DataTable(); // the table
    var selected_row = table.row(this).data(); // the selected row data
   
    if (current[0].id == 'tacview_kills') {
        var kill_id = selected_row[selected_row.length - 1].toString();
        console.log(kill_id);
        window.location.href = '#killcam';
        var elem = document.getElementById('killcam');
        set_onclick(elem, kill_id);
        return;
    } else if (current[0].id == 'tacview') {
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
    };
});


// function load_chart(path, pctile) {
//     console.log("Loading chart for: " + path);
//     var timeFormat = "YYYY-MM-DD HH:mm:ss";
//     var chart_nm = path + "_chart";
//     $.getJSON("/" + path + "?pctile=" + pctile,
//         function (data) {

//             var ctx = document.getElementById(chart_nm).getContext('2d');
//             var chart = new Chart(ctx, {
//                 type: 'line',
//                 // labels: ['Percentile 10 FPS'],
//                 data: {
//                     labels: data.labels,
//                     datasets: [{
//                         data: data.data,
//                         label: 'Percentile 10 FPS'
//                     }],
//                 },
//                 options: {
//                     // showLine: true,
//                     scales: {
//                         xAxes: [{
//                             type: 'time',
//                             time: {
//                                 parser: timeFormat,
//                                 unit: 'second',
//                                 // round: 'day'
//                                 tooltipFormat: 'YYYY-MM-DD HH:mm:ss',
//                                 // displayFormats: {
//                                 //   second: 'h:mm:ss a',
//                                 //     minute: 'HH:mm',
//                                 //     hour: 'HH'
//                                 // }
//                             }
//                             // display: true,
//                             // scaleLabel: {
//                             //     display: true,
//                             //     labelString: 'Time'
//                             // }
//                         }]

//                         //       xAxes: [{
//                         //         type: 'time',
//                         //         scaleLabel: {
//                         //                   display:     true,
//                         //                   labelString: 'Date'
//                         //               },
//                         //         time:       {
//                         //           unit: 'second',
//                         //           parser: timeFormat,
//                         //           tooltipFormat: 'll'
//                         //         },
//                         //       }]
//                     }
//                 }
//             });

//         });
// }