/*
  NTXEC session dashboard: iframe auto-resize helper.
  Add data-ntxec-dashboard to the iframe and load this script once on the page.
  The dashboard reports its height; this script sizes the matching iframe so it
  shows without an inner scroll bar. Without this script the iframe still works,
  using its own min-height and scrolling inside the frame.
*/
(function () {
  if (window.__ntxecDashboardEmbed) return;
  window.__ntxecDashboardEmbed = true;
  window.addEventListener("message", function (e) {
    var msg = e.data;
    if (!msg || msg.type !== "ntxec-dashboard-height" || typeof msg.height !== "number") return;
    var frames = document.querySelectorAll("iframe[data-ntxec-dashboard]");
    for (var i = 0; i < frames.length; i++) {
      if (frames[i].contentWindow === e.source) {
        var h = Math.max(400, Math.min(20000, Math.round(msg.height)));
        frames[i].style.height = h + "px";
        frames[i].setAttribute("scrolling", "no");
      }
    }
  });
})();
