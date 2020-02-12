/*jshint esversion: 6 */
function clear_table(table_id) {
  console.log("Destroying table " + table_id);
  table = $("#" + table_id + "_tbl").dataTable();
  table.fnClearTable();
  table.fnDestroy();

  // Remove the datatable body and header nodes
  var tbl_node = document.getElementById(table_id + "_tbl");
  while (tbl_node.firstChild) {
    tbl_node.removeChild(tbl_node.firstChild);
  }
}

function load_chart(path, pctile) {
  console.log("Loading chart for: " + path);
  var timeFormat = "YYYY-MM-DD HH:mm:ss";
  var chart_nm = path + "_chart";
  jQuery.getJSON("/" + path + "?pctile=" + pctile,
    function( data ) {

      var ctx = document.getElementById(chart_nm).getContext('2d');
      var chart = new Chart(ctx, {
        type: 'line',
        // labels: ['Percentile 10 FPS'],
        data: {
          labels: data.labels,
          datasets : [{
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
  if ($.fn.dataTable.isDataTable(tbl_nm)) {
    $(tbl_nm).DataTable().destroy();
    $(tbl_nm).empty();
  }

  jQuery.getJSON("/" + path, function( data ) {

  var cols = [];
  for (i = 0; i < data.columns.length; i++) {
    var col_nm = data.columns[i].split("_");
    for (var n = 0; n < col_nm.length; n++) {
      col_nm[n] = col_nm[n].charAt(0).toUpperCase() + col_nm[n].slice(1);
    }
    var col_nm = {"title": col_nm.join(" ")};
    if (col_nm.title === 'Session Date') {
        col_nm.render = function(data, type) {
            return type === 'sort' ? data : moment(data).format('L');
        };
    }
    cols.push(col_nm);
  }

  var sortKeys = {
    "overall":  [[ 1, "desc" ]],
    "session_performance": [],
    "stat_logs":  [[ 1, "desc" ]],
    "weapon_db": [],
    "tacview": [],
    "weapons": [3, 'desc'],
    "losses": [[1, "desc"]],
    "kills": [[3, "desc"]],
    "frametime_logs": [[1, "desc"]]
  };

  console.log("Loading table: " + path);
  $(tbl_nm).DataTable({
    destroy: true,
    data: data.data,
    columns: cols,
    order: sortKeys[path],
    paging: false,
    pageLength: 50,
    rowId: "index",
    fixedColumns: false,
    autoWidth: true,
    lengthChange : false,
    scrollY: 600,
    info: false,
    scrollX: true,
    sScrollX: "100%",
  });
});
}


var btnContainer = document.getElementById("nav_set");
// Get all buttons with class="btn" inside the container
var btns = btnContainer.getElementsByClassName("nav-link");
// Loop through the buttons and add the active class to the current/clicked button
for (var i = 0; i < btns.length; i++) {
  btns[i].addEventListener("click", function() {
    var current = document.getElementsByClassName("active");
    // If there's no active class
    if (current.length > 0) {
        try {
        //   if ( $.fn.dataTable.isDataTable("#" + current[0].id + "_tbl" ) &
        //         current[0].href.slice(-1) === "#"){
        //           // Only call desctructor if object is already a datatable AND
        //           // the href on current tab is for single-page-app (aka #).
        //     // clear_table(current[0].id);
        //   }else{
        //     console.log("No table initialized for tag #" + current[0].id+ "_tbl");
        //     console.log(current[0].href.slice(-1));
        //   }
          current[0].className = current[0].className.replace(" active", "");
        }catch(e){
          console.log(e.stack);
        }
    }
    // Add the active class to the current/clicked button
    this.className += " active";
    if (this.id === "frametime_charts") {
      load_chart(this.id, 50);
    }else{
        console.log("Table init...");
        load_dt(this.id);
    }
  });
}


$(document).ready(function() {
  // document.getElementById("overall_container").style.visibility = "visible";
  load_dt("overall");
});
