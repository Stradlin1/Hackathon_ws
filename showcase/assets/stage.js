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
  /* ---------------- slide 04: projected vector plane ---------------- */
  function initVectorMap() {
    var host = document.getElementById("vecMap");
    var readout = document.getElementById("vmCos");
    if (!host) return;
    var block = data().principles;
    if (!block || !block.matrix || !block.bridge || !block.bridge.zh_scores) {
      host.innerHTML = '<p class="vm-empty">这一页的投影需要中文文本向量；本机没有生成。</p>';
      return;
    }

    var labels = block.matrix.labels;
    var values = block.matrix.values;
    var zh = block.bridge.zh_scores;
    var n = labels.length;
    var N = n + 1;
    var textIndex = n;
    var i, j;

    // 7x7 cosine matrix: six photos from the heatmap, one Chinese sentence from the bridge.
    var G = [];
    for (i = 0; i < N; i++) {
      G.push([]);
      for (j = 0; j < N; j++) G[i].push(0);
    }
    for (i = 0; i < n; i++) {
      for (j = 0; j < n; j++) G[i][j] = values[i][j];
      G[textIndex][i] = zh[i];
      G[i][textIndex] = zh[i];
    }
    G[textIndex][textIndex] = 1;

    // Classical MDS: B = -1/2 * J * (1 - G) * J, then the top two eigenvectors.
    var D = [], rowMean = [], total = 0;
    for (i = 0; i < N; i++) {
      D.push([]);
      var sum = 0;
      for (j = 0; j < N; j++) { D[i].push(1 - G[i][j]); sum += D[i][j]; }
      rowMean.push(sum / N);
      total += sum / N;
    }
    total /= N;
    var B = [];
    for (i = 0; i < N; i++) {
      B.push([]);
      for (j = 0; j < N; j++) B[i].push(-0.5 * (D[i][j] - rowMean[i] - rowMean[j] + total));
    }

    function topEigen(M, count) {
      var A = M.map(function (row) { return row.slice(); });
      var vecs = [], vals = [];
      for (var k = 0; k < count; k++) {
        var v = A.map(function (_, index) { return index === k ? 1 : (index + 1) / (N + 2); });
        var lambda = 0;
        for (var it = 0; it < 260; it++) {
          var w = A.map(function (row) {
            return row.reduce(function (acc, value, index) { return acc + value * v[index]; }, 0);
          });
          var norm = Math.sqrt(w.reduce(function (acc, value) { return acc + value * value; }, 0));
          if (norm < 1e-9) break;
          v = w.map(function (value) { return value / norm; });
          lambda = norm;
        }
        vecs.push(v);
        vals.push(lambda);
        for (var r = 0; r < N; r++) {
          for (var c = 0; c < N; c++) A[r][c] -= lambda * v[r] * v[c];
        }
      }
      return { vals: vals, vecs: vecs };
    }

    var eigen = topEigen(B, 2);
    var coords = labels.concat("失主的话").map(function (_, index) {
      var x = eigen.vecs[0][index] * Math.sqrt(Math.max(0, eigen.vals[0]));
      var y = eigen.vecs[1] ? eigen.vecs[1][index] * Math.sqrt(Math.max(0, eigen.vals[1])) : 0;
      return { x: x, y: y };
    });
    if (coords[textIndex].x < 0) coords.forEach(function (point) { point.x = -point.x; });
    if (coords[textIndex].y < 0) coords.forEach(function (point) { point.y = -point.y; });

    var best = 0;
    zh.forEach(function (value, index) { if (value > zh[best]) best = index; });

    function draw() {
      var width = Math.max(260, host.clientWidth || 360);
      var height = Math.max(140, host.clientHeight || 190);
      var pad = 34;
      var xs = coords.map(function (point) { return point.x; });
      var ys = coords.map(function (point) { return point.y; });
      var spanX = Math.max(1e-6, Math.max.apply(null, xs) - Math.min.apply(null, xs));
      var spanY = Math.max(1e-6, Math.max.apply(null, ys) - Math.min.apply(null, ys));
      var scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
      var offsetX = (width - spanX * scale) / 2 - Math.min.apply(null, xs) * scale;
      var offsetY = (height - spanY * scale) / 2 - Math.min.apply(null, ys) * scale;
      var points = coords.map(function (point) {
        return { x: point.x * scale + offsetX, y: point.y * scale + offsetY };
      });

      var NS = "http://www.w3.org/2000/svg";
      function el(tag, attrs) {
        var node = document.createElementNS(NS, tag);
        for (var key in attrs) if (attrs.hasOwnProperty(key)) node.setAttribute(key, attrs[key]);
        return node;
      }

      host.textContent = "";
      var canvas = el("svg", { viewBox: "0 0 " + width + " " + height, "aria-hidden": "true" });

      // A halo around the photo cluster: they really do sit close together.
      var clipX = points.slice(0, n).map(function (p) { return p.x; });
      var clipY = points.slice(0, n).map(function (p) { return p.y; });
      var cx = (Math.min.apply(null, clipX) + Math.max.apply(null, clipX)) / 2;
      var cy = (Math.min.apply(null, clipY) + Math.max.apply(null, clipY)) / 2;
      var rx = Math.max(26, (Math.max.apply(null, clipX) - Math.min.apply(null, clipX)) / 2 + 14);
      var ry = Math.max(26, (Math.max.apply(null, clipY) - Math.min.apply(null, clipY)) / 2 + 16);
      canvas.appendChild(el("ellipse", { class: "vm-halo", cx: cx, cy: cy, rx: rx, ry: ry }));

      var textPoint = points[textIndex];
      var bestPoint = points[best];
      canvas.appendChild(el("line", {
        class: "vm-link",
        x1: textPoint.x, y1: textPoint.y,
        x2: bestPoint.x, y2: bestPoint.y
      }));

      var midX = (textPoint.x + bestPoint.x) / 2;
      var midY = (textPoint.y + bestPoint.y) / 2;
      var score = el("text", { class: "vm-score", x: midX + 6, y: midY - 6 });
      score.textContent = zh[best].toFixed(3);
      canvas.appendChild(score);

      points.forEach(function (point, index) {
        var isText = index === textIndex;
        var dot = el("circle", {
          cx: point.x, cy: point.y,
          r: isText ? 5.5 : (index === best ? 5 : 4),
          class: "vm-point " + (isText ? "vm-pt-text" : "vm-pt-photo") + (index === best ? " vm-pt-best" : "")
        });
        dot.style.setProperty("--i", String(index));
        dot.dataset.label = isText ? "失主的话" : labels[index];
        dot.dataset.cos = isText ? "" : zh[index].toFixed(3);
        dot.setAttribute("tabindex", "0");
        dot.setAttribute("role", "button");
        dot.setAttribute("aria-label", isText ? "失主的话" : labels[index] + "，与失主的话 cos " + zh[index].toFixed(3));
        canvas.appendChild(dot);
        if (index === best) {
          var ring = el("circle", { class: "vm-ring", cx: point.x, cy: point.y, r: 8 });
          canvas.appendChild(ring);
        }
      });

      function labelFor(index, text, options) {
        var point = points[index];
        var attrs = { class: "vm-label", x: point.x + options.dx, y: point.y + options.dy };
        if (options.anchor) attrs["text-anchor"] = options.anchor;
        var label = el("text", attrs);
        label.textContent = text;
        return label;
      }
      canvas.appendChild(labelFor(textIndex, "失主的话", { dx: 9, dy: 4 }));
      canvas.appendChild(labelFor(best, labels[best], { dx: -9, dy: 4, anchor: "end" }));
      var cluster = el("text", { class: "vm-label vm-label-quiet", x: cx, y: cy - ry - 2, "text-anchor": "middle" });
      cluster.textContent = n + " 张拾获照片";
      canvas.appendChild(cluster);

      host.appendChild(canvas);

      function resetReadout() {
        if (readout) readout.textContent = "最近：" + labels[best] + " · " + zh[best].toFixed(3);
      }
      Array.prototype.forEach.call(canvas.querySelectorAll(".vm-point"), function (dot) {
        function show() {
          if (!readout) return;
          readout.textContent = dot.dataset.cos
            ? dot.dataset.label + " · cos " + dot.dataset.cos
            : "失主的话 · 与 " + n + " 张照片比较";
        }
        dot.addEventListener("mouseenter", show);
        dot.addEventListener("click", show);
        dot.addEventListener("focus", show);
        dot.addEventListener("mouseleave", resetReadout);
        dot.addEventListener("blur", resetReadout);
      });
    }

    var resizeTimer = null;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(draw, 180);
    });
    window.__drawVectorMap = draw;
    draw();
  }

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

    initVectorMap();

    function revealMap() {
      if (window.__drawVectorMap) window.__drawVectorMap();
    }

    document.getElementById("runSemantic").addEventListener("click", function () {
      reveal();
      revealMap();
    });
    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { reveal(); revealMap(); observer.disconnect(); }
        });
      }, { threshold: 0.6 });
      observer.observe(document.getElementById("s3b"));
    } else {
      reveal();
      revealMap();
    }
  }

  /* ---------------- slides 05 / 06: principles ---------------- */
  function initPrinciples() {
    var block = data().principles;
    if (!block) return;

    function shade(value, low, high) {
      var t = high > low ? (value - low) / (high - low) : 0.5;
      t = Math.max(0, Math.min(1, t));
      return (0.06 + t * 0.56).toFixed(2);
    }

    var labels = block.matrix.labels;
    var values = block.matrix.values;
    var band = block.matrix.band;
    var heat = document.getElementById("heatMatrix");
    var read = document.getElementById("heatRead");
    var range = document.getElementById("bandRange");
    if (range) range.textContent = band.min.toFixed(2) + " – " + band.max.toFixed(2);

    if (heat) {
      heat.style.gridTemplateColumns = "56px repeat(" + labels.length + ", 1fr)";
      heat.appendChild(node("span", "heat-corner"));
      labels.forEach(function (label) {
        var head = node("span", "heat-col", label);
        head.title = label;
        heat.appendChild(head);
      });

      var rows = [];
      labels.forEach(function (label, i) {
        var head = node("span", "heat-label", label);
        head.title = label;
        heat.appendChild(head);
        var cells = [];
        values[i].forEach(function (value, j) {
          var cell;
          if (i === j) {
            cell = node("span", "heat-cell diag", "·");
            cell.dataset.diag = "1";
          } else {
            cell = node("span", "heat-cell", value.toFixed(2));
            cell.style.setProperty("--a", shade(value, band.min, band.max));
            if (value >= 0.66) cell.className = "heat-cell light";
          }
          cell.dataset.i = String(i);
          heat.appendChild(cell);
          cells.push(cell);
        });
        rows.push({ head: head, cells: cells });
      });

      function pick(i) {
        rows.forEach(function (row, k) {
          row.head.classList.toggle("on", k === i);
          row.cells.forEach(function (cell) {
            cell.classList.toggle("on", k === i && cell.dataset.diag !== "1");
          });
        });
        var best = -1, worst = 2, bestJ = 0, worstJ = 0;
        values[i].forEach(function (value, j) {
          if (j === i) return;
          if (value > best) { best = value; bestJ = j; }
          if (value < worst) { worst = value; worstJ = j; }
        });
        read.innerHTML = "";
        read.appendChild(node("b", null, labels[i]));
        read.appendChild(document.createTextNode(
          "：和「" + labels[bestJ] + "」最像（" + best.toFixed(3) + "），和「" +
          labels[worstJ] + "」最不像（" + worst.toFixed(3) + "）。"));
      }

      heat.addEventListener("click", function (event) {
        var cell = event.target.closest(".heat-cell");
        if (cell) pick(Number(cell.dataset.i));
      });
      pick(0);
    }

    var bridge = block.bridge;
    var table = document.getElementById("bridgeTable");
    var note = document.getElementById("orderNote");
    if (!bridge) {
      if (note) note.textContent = "本机没缓存多语文本编码器，这一组对齐数字没有生成；补下载后重跑 build_demo.py 就能看到。";
      return;
    }
    document.getElementById("zhSent").textContent = bridge.zh;
    document.getElementById("enSent").textContent = bridge.en;
    document.getElementById("zhEnCos").textContent = bridge.zh_en.toFixed(3);

    if (table) {
      table.style.gridTemplateColumns = "52px repeat(" + labels.length + ", 1fr)";
      table.appendChild(node("span", "bt-corner"));
      labels.forEach(function (label) {
        var head = node("span", "bt-head", label);
        head.title = label;
        table.appendChild(head);
      });
      [["中文句", bridge.zh_scores], ["英文译句", bridge.en_scores]].forEach(function (entry) {
        table.appendChild(node("span", "bt-label", entry[0]));
        entry[1].forEach(function (value) {
          var cell = node("span", "bt-cell", value.toFixed(3));
          cell.style.setProperty("--a", shade(value, 0.14, 0.34));
          if (value >= 0.27) cell.className = "bt-cell light";
          table.appendChild(cell);
        });
      });
    }

    if (note) {
      var top = bridge.zh_scores.indexOf(Math.max.apply(null, bridge.zh_scores));
      note.textContent = bridge.same_order
        ? "两行的绝对分不同（" + bridge.zh_scores[top].toFixed(3) + " / " + bridge.en_scores[top].toFixed(3) +
          "），但 6 张照片的顺序完全一致：中文句落在英文译句旁边，这就是「挂上」。"
        : "两句话给出的顺序并不完全一致——多语文本塔和英文文本塔不是同一个模型。";
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
      initPrinciples();
      initEvidence();
      initExplain();
      initClarify();
      initPrivacy();
      initPaths();
      var openApp = document.getElementById("openApp");
      if (openApp && payload.meta && payload.meta.app_lan) {
        openApp.href = payload.meta.app_lan.replace(/\/$/, "") + "/";
      }
    })
    .catch(function (error) {
      fail("数据没有加载成功（" + error.message + "）");
    });
})();
