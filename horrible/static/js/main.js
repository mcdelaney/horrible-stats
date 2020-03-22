/*jshint esversion: 6 */

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
    ]
};


function load_chart(path, pctile) {
    console.log("Loading chart for: " + path);
    var timeFormat = "YYYY-MM-DD HH:mm:ss";
    var chart_nm = path + "_chart";
    jQuery.getJSON("/" + path + "?pctile=" + pctile,
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

function load_dt(path) {
    var tbl_nm = "#overall_tbl";

    console.log("Checking that table exists...");
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

    jQuery.getJSON("/" + path, function (data) {

        var cols = [];
        for (i = 0; i < data.columns.length; i++) {
            var col_nm = data.columns[i].split("_");
            for (var n = 0; n < col_nm.length; n++) {
                col_nm[n] = col_nm[n].charAt(0).toUpperCase() + col_nm[n].slice(1);
            }
            col_nm = {
                "title": col_nm.join(" ")
            };
            if (col_nm.title === 'Session Date') {
                col_nm.render = function (data, type) {
                    return type === 'sort' ? data : moment(data).format('L');
                };
            }
            cols.push(col_nm);
        }

        console.log("Loading table: " + path);
        $(tbl_nm).DataTable({
            data: data.data,
            columns: cols,
            order: sortKeys[path],
            paging: false,
            pageLength: 50,
            rowId: "index",
            fixedColumns: false,
            autoWidth: true,
            lengthChange: false,
            scrollY: 600,
            info: false,
            scrollX: true,
            sScrollX: "100%",
        });

        document.getElementById('load_spin').hidden = true;
        document.getElementById('overall_container').hidden = false;
    });
}


function set_onclick() {
    var current = document.getElementsByClassName("active");
    // If there's no active class
    if (current.length > 0) {
        current[0].className = current[0].className.replace(" active", "");
    }
    // Add the active class to the current/clicked button
    this.className += " active";
    if (this.id === "killcam") {
        // document.getElementById('killcam_div').hidden = true;

        var offset = 20;
        var pilot = "someone_somewhere";
        document.getElementById('load_spin').hidden = true;
        document.getElementById('overall_container').hidden = true;
        document.getElementById('killcam_div').hidden = false;

        if (scene != null) {
            console.log('Clearing scene...');
            while (scene.children.length > 0) {
                scene.remove(scene.children[0]);
            }
            var killcam_canv = document.getElementById('killcam_canv');
            killcam_canv.parentNode.removeChild(killcam_canv);

        }

        var prev_info = document.getElementById('killcam_info');
        if (prev_info != null) {
            prev_info.parentNode.removeChild(prev_info);
        }

        load_kill(pilot, offset);
    } else {
        console.log("Table init...");
        load_dt(this.id);
    }
}

function set_tab_active() {
    var btnContainer = document.getElementById("nav_set");
    // Get all buttons with class="btn" inside the container
    var btns = btnContainer.getElementsByClassName("nav-link");
    // Loop through the buttons and add the active class to the current/clicked button
    for (var i = 0; i < btns.length; i++) {
        btns[i].addEventListener("click", set_onclick);
    }
}


$(document).ready(function () {
    set_tab_active();
    load_dt("overall");
});

var selected_row;

$('#overall_tbl').on('click', 'tbody tr', function () {
    // For table clicks...
    var current = document.getElementsByClassName("active");
    if (current[0].id != 'tacview') {
        return;
    }
    var table = $('#overall_tbl').DataTable();
    selected_row = table.row(this).data();

    //now use AJAX with data, which is on the form [ { col1 : value, col2: value ..}]
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
            // var table = $('#overall_tbl').DataTable();
            // table.cell({row: 1, column: 2}).data("Error");
            // table.draw();
        }
    });

});