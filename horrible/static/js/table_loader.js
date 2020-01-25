
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


function load_dt(path) {
  console.log("Loading table: " + path);

  // jQuery node accessor for table.  Matches html tag.
  var tbl_nm = "#" +  path + "_tbl";

  var colKeys = {
    "overall":  [
      { "title":"Pilot" },
      { "title":"Category" },
      { "title":"Stat Type" },
      { "title":"Sub Type" },
      { "title":"Value" }
    ],
    "weapon_db": [
      { "title":"Name" },
      { "title":"Category" },
      { "title":"Type" }
    ],
    "tacview": [
      {"title": "Status"}
    ],
    "stat_logs": [
      { "title":"File Name" },
      { "title":"Session Start Time" },
      { "title":"Processed" },
      { "title":"Processed At" },
      { "title":"Errors" }
    ]
  };

  var sortKeys = {
    "overall":  [[ 4, "desc" ]],
    "stat_logs":  [[ 1, "desc" ]],
    "weapon_db": [],
    "tacview": []
  }

  $(tbl_nm).DataTable({
    ajax: {
      url: "/" + path,
      dataSrc: 'data'
    },
    columns:colKeys[path],
    order: sortKeys[path],
    // rowGroup: {
    //     dataSrc: [ 1, 0, 2,3 ]
    // },
    // columnDefs: [ {
    //     targets: [ 0, 1, 2, 3 ],
    //     visible: false
    // } ],
    paging: false,
    pageLength: 50,
    rowId: "index",
    fixedColumns: false,
    autoWidth: true,
    lengthChange : false,
    scrollY: 500,
    scrollX: true,
    sScrollX: "100%",
  });
};


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
          if ( $.fn.dataTable.isDataTable("#" + current[0].id + "_tbl" ) &
                current[0].href.slice(-1) === "#"){
                // current[0].href === "#") {
                  // Only call desctructor if object is already a datatable AND
                  // the href on current tab is for single-page-app (aka #).
            clear_table(current[0].id)
          }else{
            console.log("No table initialized for tag #" + current[0].id+ "_tbl")
            console.log(current[0].href.slice(-1))
          }
          current[0].className = current[0].className.replace(" active", "");
        }catch(e){
          console.log(e.stack);
        };
    }
    // Add the active class to the current/clicked button
    this.className += " active";
    var tbl_container = document.getElementById("table_container");
    var active_tbl = document.getElementById(this.id + "_tbl");
    tbl_container.prepend(active_tbl);
    load_dt(this.id);
  });
}




$(document).ready(function() {
  // document.getElementById("overall_container").style.visibility = "visible";
  load_dt("overall");
});
