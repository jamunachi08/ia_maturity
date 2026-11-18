// Restrict native Desk chrome to the GRC staff page. Authorization remains server-side.
if (frappe.boot?.grc_staff) {
 frappe.boot.setup_complete=true;
 frappe.boot.sysdefaults.setup_complete=1;
 frappe.boot.desk_settings.notifications=0;
 frappe.boot.desk_settings.search_bar=0;
 frappe.boot.navbar_settings.announcement_widget="";
 frappe.realtime.init=()=>{};
 localStorage.removeItem("session_last_route");
 $(document).on("toolbar_setup",()=>{
  $(".navbar .search-bar,.navbar .dropdown-notifications,.navbar .dropdown-help").hide();
  // /app on v15, /desk on v16: keep whichever prefix this Desk is served under.
  const deskBase = "/" + (window.location.pathname.split("/")[1] || "app");
  $(".navbar-brand").attr("href", deskBase + "/grc-staff");
 });
}
