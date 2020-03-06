/*jshint esversion: 6 */


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

        var sortKeys = {
            "overall": [
                [2, "desc"]
            ],
            "session_performance": [],
            "stat_logs": [
                [1, "desc"]
            ],
            "weapon_db": [],
            "tacview": [],
            "events": [[1, "desc"]],
            "weapons": [3, 'desc'],
            "losses": [
                [1, "desc"]
            ],
            "kills": [
                [3, "desc"]
            ],
            "frametime_logs": [
                [1, "desc"]
            ]
        };

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


var btnContainer = document.getElementById("nav_set");
// Get all buttons with class="btn" inside the container
var btns = btnContainer.getElementsByClassName("nav-link");
// Loop through the buttons and add the active class to the current/clicked button
for (var i = 0; i < btns.length; i++) {
    btns[i].addEventListener("click", function () {
        var current = document.getElementsByClassName("active");
        // If there's no active class
        if (current.length > 0) {
            current[0].className = current[0].className.replace(" active", "");
        }
        // Add the active class to the current/clicked button
        this.className += " active";
        if (this.id === "killcam") {

            // document.getElementById('killcam_div').hidden = true;
            document.getElementById('overall_container').hidden = true;
            document.getElementById('load_spin').hidden = false;

            var offset = 20;
            var pilot = "someone_somewhere";
            load_kill(pilot, offset);
            // load_chart(this.id, 50);
        } else {
            console.log("Table init...");
            load_dt(this.id);
        }
    });
}


$(document).ready(function () {
    load_dt("overall");
});