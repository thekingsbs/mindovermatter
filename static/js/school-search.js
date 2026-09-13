// Client-side filter for the school picker. No search backend needed for a
// handful of chapters: filter the pre-rendered list on input. Each item links
// to a chapter slug, so nothing free-text is ever submitted.
(function () {
  var input = document.querySelector("[data-school-search]");
  if (!input) return;
  var items = Array.prototype.slice.call(document.querySelectorAll(".school-list li"));
  input.addEventListener("input", function () {
    var q = input.value.trim().toLowerCase();
    items.forEach(function (li) {
      var name = (li.getAttribute("data-name") || "").toLowerCase();
      li.hidden = q !== "" && name.indexOf(q) === -1;
    });
  });
})();
