(function () {
  "use strict";

  var deck = document.getElementById("deck");
  var toastEl = document.getElementById("toast");
  var toastTimer = null;

  function toast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, 2200);
  }

  function node(tag, className, text) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    if (text != null) el.textContent = text;
    return el;
  }

  function fail(message) {
    deck.innerHTML = '<section class="slide in"><div class="wrap"><p class="kicker">showcase</p>' +
      '<h1>' + message + '</h1><p class="lede">先运行 <code>python showcase/build_demo.py</code>，' +
      '再用 <code>./showcase/serve.sh</code> 打开本页（file:// 下浏览器会拦截数据加载）。</p></div></section>';
  }

  function flip(container, mutate) {
    var first = {};
    Array.prototype.forEach.call(container.children, function (child) {
      first[child.dataset.id] = child.getBoundingClientRect().top;
    });
    mutate();
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    Array.prototype.forEach.call(container.children, function (child) {
      var before = first[child.dataset.id];
      if (before == null) return;
      var delta = before - child.getBoundingClientRect().top;
      if (!delta) return;
      child.animate([{ transform: "translateY(" + delta + "px)" }, { transform: "none" }],
        { duration: 520, easing: "cubic-bezier(.2,.7,.2,1)" });
    });
  }

  function short(text, limit) {
    return text.length > limit ? text.slice(0, limit) + "…" : text;
  }

  function candidateNode(row, options) {
    options = options || {};
    var li = node("li", "cand");
    li.dataset.id = String(row.id);
    if (row.expected) li.dataset.expected = "1";

    if (row.photo) {
      var img = node("img");
      img.src = row.photo;
      img.alt = "";
      img.loading = "lazy";
      img.addEventListener("error", function () { img.style.display = "none"; });
      li.appendChild(img);
    } else {
      li.appendChild(node("span", "thumb"));
    }

    var body = node("div", "body");
    body.appendChild(node("p", null, short(row.desc, options.clamp || 54)));
    var meta = "";
    if (row.matches && row.matches.length) meta += "一致 " + row.matches.join(" · ");
    if (row.conflicts && row.conflicts.length) meta += (meta ? "　" : "") + "矛盾 " + row.conflicts.join(" · ");
    body.appendChild(node("small", null, meta || "没有可比的属性"));
    li.appendChild(body);

    li.appendChild(node("span", "score", Number(row.score).toFixed(3)));
    li.appendChild(node("span", "flag", "最像"));
    var bar = node("i", "bar");
    li.appendChild(bar);
    li._bar = bar;
    li._row = row;
    return li;
  }

  function paintBars(container, key, animate) {
    Array.prototype.forEach.call(container.children, function (child) {
      var row = child._row;
      if (!row || !child._bar) return;
      var value = key === "semantic" ? row.semantic : row.score;
      if (animate) {
        child._bar.style.width = "0%";
        requestAnimationFrame(function () {
          requestAnimationFrame(function () { child._bar.style.width = (value * 100) + "%"; });
        });
      } else {
        child._bar.style.width = (value * 100) + "%";
      }
    });
  }

  function markTop(container) {
    var first = container.firstElementChild;
    Array.prototype.forEach.call(container.children, function (child) {
      child.classList.toggle("top", child === first);
    });
  }

  function data() {
    return window.__SHOWCASE__;
  }

  /* ---------------- navigation ---------------- */
  function initNav() {
    var sections = Array.prototype.slice.call(document.querySelectorAll(".slide"));
    var dots = Array.prototype.slice.call(document.querySelectorAll(".dots a"));
    var hud = document.getElementById("hudPage");

    function indexOf(section) { return sections.indexOf(section); }

    function activate(section) {
      var i = indexOf(section);
      if (i < 0) return;
      dots.forEach(function (dot, k) { dot.classList.toggle("active", k === i); });
      if (hud) hud.textContent = String(i + 1).padStart(2, "0") + " / " + String(sections.length).padStart(2, "0");
    }

    if ("IntersectionObserver" in window) {
      var spy = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("in");
          activate(entry.target);
        });
      }, { threshold: 0.55 });
      sections.forEach(function (section) { spy.observe(section); });
    } else {
      sections.forEach(function (section) { section.classList.add("in"); });
      activate(sections[0]);
    }

    function current() {
      var mid = window.innerHeight / 2;
      var best = sections[0];
      var bestDistance = Infinity;
      sections.forEach(function (section) {
        var rect = section.getBoundingClientRect();
        var distance = Math.abs(rect.top + rect.height / 2 - mid);
        if (distance < bestDistance) { bestDistance = distance; best = section; }
      });
      return best;
    }

    function go(delta) {
      var i = indexOf(current()) + delta;
      if (i < 0 || i >= sections.length) return;
      sections[i].scrollIntoView({ behavior: "smooth", block: "start" });
    }

    document.addEventListener("keydown", function (event) {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.target && /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName)) return;
      if (event.key === "ArrowRight" || event.key === "ArrowDown" || event.key === "PageDown" || event.key === " ") {
        event.preventDefault(); go(1);
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp" || event.key === "PageUp") {
        event.preventDefault(); go(-1);
      } else if (event.key === "Home") {
        event.preventDefault(); sections[0].scrollIntoView({ behavior: "smooth" });
      } else if (event.key === "End") {
        event.preventDefault(); sections[sections.length - 1].scrollIntoView({ behavior: "smooth" });
      }
    });
  }

  /* ---------------- slide 02 ---------------- */
  function initBridge() {
    var button = document.getElementById("bridgeBtn");
    var wrap = document.querySelector("#s2 .wrap");
    if (!button || !wrap) return;
    button.addEventListener("click", function () { wrap.classList.toggle("highlight"); });
    button.addEventListener("mouseenter", function () { wrap.classList.add("highlight"); });
    button.addEventListener("mouseleave", function () { wrap.classList.remove("highlight"); });
  }

  /* ---------------- slide 03 ---------------- */
  function initMatch() {
    var rows = data().candidates;
    var list = document.getElementById("candList");
    var run = document.getElementById("runMatch");
    var seg = document.querySelector("#s3 .seg");
    var mode = "evidence";

    document.getElementById("queryDesc").textContent = data().pair.lost.desc;
    document.getElementById("queryLoc").textContent = "最后出现：" + data().pair.lost.location;

    var chips = document.getElementById("queryChips");
    Object.keys(data().pair.lost.attrs || {}).forEach(function (key) {
      var chip = node("span", "chip", key);
      chip.appendChild(node("b", null, data().pair.lost.attrs[key]));
      chips.appendChild(chip);
    });

    rows.forEach(function (row) { list.appendChild(candidateNode(row)); });
    markTop(list);

    function order(key) {
      var sorted = rows.slice().sort(function (a, b) {
        return (key === "semantic" ? b.semantic - a.semantic : b.score - a.score);
      });
      flip(list, function () {
        sorted.forEach(function (row) {
          var existing = list.querySelector('[data-id="' + row.id + '"]');
          if (existing) list.appendChild(existing);
        });
      });
      markTop(list);
      paintBars(list, key, true);
    }

    run.addEventListener("click", function () {
      run.disabled = true;
      run.textContent = "匹配完成";
      order(mode);
      toast("按排序指标重新排列了 6 个候选");
    });

    seg.addEventListener("click", function (event) {
      var button = event.target.closest("button[data-mode]");
      if (!button) return;
      mode = button.dataset.mode;
      Array.prototype.forEach.call(seg.querySelectorAll("button"), function (b) {
        b.classList.toggle("on", b === button);
      });
      order(mode);
    });
  }

  /* ---------------- slide 04 ---------------- */
  function initExplain() {
    var rows = data().candidates.slice(0, 5);
    var list = document.getElementById("explainList");
    var title = document.getElementById("explainTitle");
    var scoreOut = document.getElementById("explainScore");
    var attrsOut = document.getElementById("attrRows");
    var slider = document.getElementById("mixSlider");
    var mixSem = document.getElementById("mixSem");
    var mixEv = document.getElementById("mixEv");
    var mix = 0.72;
    var selected = rows[0];

    function blended(row) {
      var score = mix * row.semantic + (1 - mix) * row.evidence01 + (row.prior || 0);
      return Math.max(0, Math.min(1, score));
    }

    function render() {
      rows.slice().sort(function (a, b) { return blended(b) - blended(a); }).forEach(function (row) {
        var card = list.querySelector('[data-id="' + row.id + '"]');
        if (!card) return;
        card.classList.toggle("selected", row.id === selected.id);
        var value = blended(row);
        card.querySelector(".score").textContent = value.toFixed(3);
        card._bar.style.width = (value * 100) + "%";
      });
    }

    function show(row) {
      selected = row;
      title.textContent = short(row.desc, 30);
      scoreOut.textContent = blended(row).toFixed(3);
      attrsOut.innerHTML = "";
      ["类型", "颜色", "材质", "形状", "品牌", "特殊标记"].forEach(function (key) {
        var value = (row.attrs || {})[key];
        var li = node("li");
        li.appendChild(node("span", "k", key));
        li.appendChild(node("span", "v" + (value ? "" : " empty"), value || "未提及"));
        var state = node("span", "state-dot na", "—");
        if (row.matches && row.matches.indexOf(key) >= 0) { state.className = "state-dot ok"; state.textContent = "一致"; }
        else if (row.conflicts && row.conflicts.indexOf(key) >= 0) { state.className = "state-dot bad"; state.textContent = "矛盾"; }
        li.appendChild(state);
        attrsOut.appendChild(li);
      });
      render();
    }

    rows.forEach(function (row) {
      var card = candidateNode(row, { clamp: 30 });
      card.addEventListener("click", function () { show(row); });
      list.appendChild(card);
    });

    slider.addEventListener("input", function () {
      mix = Number(slider.value) / 100;
      mixSem.textContent = Math.round(mix * 100) + "%";
      mixEv.textContent = Math.round((1 - mix) * 100) + "%";
      scoreOut.textContent = blended(selected).toFixed(3);
      flip(list, render);
    });

    show(rows[0]);
  }

  /* ---------------- slide 05 ---------------- */
  function initClarify() {
    var block = data().clarify;
    var list = document.getElementById("clarifyList");
    var options = document.getElementById("clarifyOptions");
    var verdict = document.getElementById("clarifyVerdict");
    document.getElementById("clarifyLost").textContent = block.lost;
    document.getElementById("clarifyQ").textContent = block.question;

    function paint(rows, animate) {
      if (animate) {
        flip(list, function () {
          rows.forEach(function (row) {
            var card = list.querySelector('[data-id="' + row.id + '"]');
            if (card) list.appendChild(card);
          });
        });
      } else {
        rows.forEach(function (row) { list.appendChild(candidateNode(row, { clamp: 34 })); });
      }
      markTop(list);
      Array.prototype.forEach.call(list.children, function (card, index) {
        var row = rows.filter(function (item) { return String(item.id) === card.dataset.id; })[0];
        if (row) {
          var value = Number(row.score);
          var score = card.querySelector(".score");
          if (score) score.textContent = value.toFixed(3);
          if (card._bar) card._bar.style.width = (value * 100) + "%";
        }
        var small = card.querySelector(".body small");
        if (small) small.textContent = "第 " + (index + 1) + " 位";
      });
    }

    paint(block.before, false);

    block.options.forEach(function (label, index) {
      var button = node("button", null, label);
      button.addEventListener("click", function () {
        Array.prototype.forEach.call(options.children, function (b) { b.classList.remove("chosen"); });
        button.classList.add("chosen");
        if (index === 0) {
          paint(block.after, true);
          verdict.className = "verdict done";
          verdict.textContent = "耳机 第 " + block.before_rank + " → 第 " + block.after_rank + " 位；绿色 logo 的单肩包被压下去。";
        } else {
          paint(block.before, true);
          verdict.className = "verdict";
          verdict.textContent = "回答“没有特别标记”不会改变排序：缺失属性是中性的，不扣分。";
        }
      });
      options.appendChild(button);
    });
  }

  /* ---------------- slide 06 ---------------- */
  function initPrivacy() {
    var send = document.getElementById("sendReq");
    var accept = document.getElementById("acceptReq");
    var reject = document.getElementById("rejectReq");
    var alice = document.getElementById("aliceState");
    var bob = document.getElementById("bobState");
    var contact = document.getElementById("bobContact");
    var sent = false;
    var closed = false;

    var secrets = contact.querySelectorAll(".secret");

    send.addEventListener("click", function () {
      if (closed) return toast("这条请求已经结束");
      sent = true;
      alice.textContent = "已发送，等待 bob 确认";
      alice.className = "state";
      bob.textContent = "收到一条请求，等待你处理";
      toast("请求已发出：对方看不到你的联系方式");
    });

    accept.addEventListener("click", function () {
      if (!sent) return toast("先由失主发送请求");
      if (closed) return;
      closed = true;
      contact.classList.add("revealed");
      secrets[0].textContent = data().privacy.email;
      secrets[1].textContent = data().privacy.phone;
      bob.textContent = "已接受：双方现在能看到联系方式";
      bob.className = "state ok";
      alice.textContent = "bob 已接受，联系方式已解锁";
      alice.className = "state ok";
      accept.disabled = true;
      reject.disabled = true;
    });

    reject.addEventListener("click", function () {
      if (!sent) return toast("先由失主发送请求");
      if (closed) return;
      closed = true;
      bob.textContent = "已拒绝";
      alice.textContent = "请求被拒绝，联系方式始终没有出现";
      accept.disabled = true;
      reject.disabled = true;
    });
  }

  /* ---------------- slide 07 ---------------- */
  function initPaths() {
    var out = document.getElementById("pathOut");
    Array.prototype.forEach.call(document.querySelectorAll(".layer li[data-path]"), function (item) {
      function show() { out.textContent = item.dataset.path; }
      item.addEventListener("mouseenter", show);
      item.addEventListener("focus", show);
      item.tabIndex = 0;
    });
  }

  /* ---------------- slide 03b: semantic ---------------- */
  function initSemantic() {
    var block = data().semantic;
    var textBox = document.getElementById("textBars");
    var imageBox = document.getElementById("imageBars");
    var cos = document.getElementById("cosValue");
    document.getElementById("vecText").textContent = data().pair.lost.desc;
    if (data().pair.found.photo) document.getElementById("vecPhoto").src = data().pair.found.photo;

    function bars(container, values) {
      values.forEach(function (value) {
        var bar = document.createElement("i");
        if (value < 0) bar.className = "neg";
        bar.dataset.h = String(Math.max(5, Math.abs(value) * 92));
        container.appendChild(bar);
      });
    }
    bars(textBox, block.text);
    bars(imageBox, block.image);

    function reveal() {
      [textBox, imageBox].forEach(function (container) {
        Array.prototype.forEach.call(container.children, function (bar, index) {
          setTimeout(function () { bar.style.height = bar.dataset.h + "%"; }, index * 16);
        });
      });
      var start = performance.now();
      function step(now) {
        var t = Math.min(1, (now - start) / 800);
        cos.textContent = (block.cosine * t).toFixed(3);
        if (t < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }

    document.getElementById("runSemantic").addEventListener("click", reveal);
    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { reveal(); observer.disconnect(); }
        });
      }, { threshold: 0.6 });
      observer.observe(document.getElementById("s3b"));
    } else {
      reveal();
    }
  }

  /* ---------------- slide 03c: evidence ---------------- */
  function initEvidence() {
    var examples = data().formula.examples;
    var body = document.getElementById("cmpBody");
    var toggle = document.getElementById("exampleToggle");
    var fields = ["类型", "颜色", "材质", "形状", "品牌", "特殊标记"];
    var lostAttrs = data().pair.lost.attrs || {};

    function render(index) {
      var example = examples[index];
      var candidate = data().candidates[example.candidate];
      var attrs = candidate.attrs || {};
      body.innerHTML = "";
      fields.forEach(function (key) {
        var left = lostAttrs[key];
        var right = attrs[key];
        var status = "—";
        var cls = "na";
        if (!left || !right) {
          status = "未提及";
        } else if ((candidate.matches || []).indexOf(key) >= 0) {
          status = "一致";
          cls = "ok";
        } else if ((candidate.conflicts || []).indexOf(key) >= 0) {
          status = "矛盾";
          cls = "bad";
        }
        var tr = document.createElement("tr");
        tr.innerHTML = '<td class="k">' + key + "</td><td>" + (left || "—") +
          "</td><td>" + (right || "—") + '</td><td class="' + cls + '">' + status + "</td>";
        body.appendChild(tr);
      });
      document.getElementById("fSem").textContent = example.semantic.toFixed(3);
      document.getElementById("fEv").textContent = example.evidence.toFixed(3);
      document.getElementById("fPrior").textContent = example.prior.toFixed(3);
      document.getElementById("fScore").textContent = example.score.toFixed(3);
      document.getElementById("fSemPart").textContent = (example.semantic * 0.72).toFixed(3);
      document.getElementById("fEvPart").textContent = (((example.evidence + 1) / 2) * 0.28).toFixed(3);
      document.getElementById("fPriorPart").textContent = "+" + example.prior.toFixed(3);
    }

    toggle.addEventListener("click", function (event) {
      var button = event.target.closest("button[data-i]");
      if (!button) return;
      Array.prototype.forEach.call(toggle.querySelectorAll("button"), function (item) {
        item.classList.toggle("on", item === button);
      });
      render(Number(button.dataset.i));
    });
    render(0);
  }

  /* ---------------- boot ---------------- */
  fetch("data/demo.json", { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(function (payload) {
      window.__SHOWCASE__ = payload;
      initNav();
      initBridge();
      initMatch();
      initSemantic();
      initEvidence();
      initExplain();
      initClarify();
      initPrivacy();
      initPaths();
      var appUrl = document.getElementById("appUrl");
      var openApp = document.getElementById("openApp");
      if (payload.meta && payload.meta.app_lan) {
        if (appUrl) appUrl.textContent = payload.meta.app_lan.replace("http://", "");
        if (openApp) openApp.href = payload.meta.app_lan.replace(/\/$/, "") + "/";
      }
    })
    .catch(function (error) {
      fail("数据没有加载成功（" + error.message + "）");
    });
})();
