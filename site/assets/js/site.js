(() => {
  const root = document.documentElement;
  root.classList.add("js");

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const revealTargets = document.querySelectorAll(
    ".section-head, .problem-grid, .step, .design-lede, .design-hero, .design-grid figure, .design-notes, .statement, .principles li, .stateflow, .pipeline, .tech-notes, .entries, .resources"
  );

  if (reduce || !("IntersectionObserver" in window)) {
    revealTargets.forEach((el) => el.classList.add("is-in"));
  } else {
    revealTargets.forEach((el) => el.classList.add("reveal"));
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 }
    );
    revealTargets.forEach((el) => io.observe(el));
  }

  const navLinks = [...document.querySelectorAll(".nav a")];
  const sections = navLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  if (sections.length && "IntersectionObserver" in window) {
    const spy = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          navLinks.forEach((link) => {
            const active = link.getAttribute("href") === `#${entry.target.id}`;
            link.style.color = active ? "var(--ink)" : "";
            link.style.borderColor = active ? "var(--ink)" : "";
          });
        });
      },
      { rootMargin: "-45% 0px -45% 0px" }
    );
    sections.forEach((section) => spy.observe(section));
  }

  const aiLink = document.getElementById("ai-demo-link");
  if (aiLink && aiLink.getAttribute("href") === "#ai-pending") {
    aiLink.addEventListener("click", (event) => {
      event.preventDefault();
      document.getElementById("ai-pending").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
    });
  }
})();
