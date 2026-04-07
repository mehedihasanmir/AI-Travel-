const chatEl = document.getElementById("chat");
    const formEl = document.getElementById("chatForm");
    const promptEl = document.getElementById("prompt");
    const sendBtnEl = document.getElementById("sendBtn");
    const apiBaseEl = document.getElementById("apiBase");
    const sessionIdEl = document.getElementById("sessionId");
    const sessionListEl = document.getElementById("sessionList");
    const newSessionEl = document.getElementById("newSession");
    const syncIndicatorEl = document.getElementById("syncIndicator");
    const statusEl = document.getElementById("status");
    const detailsModalOverlayEl = document.getElementById("detailsModalOverlay");
    const detailsModalBodyEl = document.getElementById("detailsModalBody");
    const detailsModalTitleEl = document.getElementById("detailsModalTitle");
    const detailsModalCloseEl = document.getElementById("detailsModalClose");
    let activeSessionId = sessionIdEl.value.trim() || "user-session-1";
    let sessionCache = [];
    let sessionSyncState = "saved";
    const LOCAL_SESSION_TITLES_KEY = "ai-travel-session-titles";

    // Use same origin only when page is served by FastAPI UI route.
    // If opened from Live Server or file, fall back to local API server.
    const servedByFastApi =
      /^https?:$/i.test(window.location.protocol) &&
      (window.location.port === "8000" || window.location.pathname === "/ui");

    const defaultApiBase = servedByFastApi
      ? window.location.origin
      : "http://127.0.0.1:8000";
    apiBaseEl.value = defaultApiBase;

    function setStatus(text) {
      statusEl.textContent = text || "";
    }

    function createSessionId() {
      const rand = Math.random().toString(36).slice(2, 8);
      return `session-${Date.now()}-${rand}`;
    }

    function autoResizePrompt() {
      promptEl.style.height = "auto";
      const next = Math.min(promptEl.scrollHeight, 140);
      promptEl.style.height = `${next}px`;
    }

    function generateTitleFromPrompt(prompt) {
      const text = String(prompt || "").trim().replace(/\s+/g, " ");
      if (!text) return "New Chat";
      if (text.length <= 60) return text;
      return text.slice(0, 57).trim() + "...";
    }

    function readLocalSessionTitles() {
      try {
        const raw = window.localStorage.getItem(LOCAL_SESSION_TITLES_KEY);
        return raw ? JSON.parse(raw) : {};
      } catch (err) {
        return {};
      }
    }

    function writeLocalSessionTitles(map) {
      try {
        window.localStorage.setItem(LOCAL_SESSION_TITLES_KEY, JSON.stringify(map || {}));
      } catch (err) {
        // Ignore storage failures.
      }
    }

    function saveLocalSessionTitle(sessionId, title) {
      const sid = String(sessionId || "").trim();
      const ttl = String(title || "").trim();
      if (!sid || !ttl) return;
      const map = readLocalSessionTitles();
      map[sid] = ttl;
      writeLocalSessionTitles(map);
    }

    function getLocalSessionTitle(sessionId) {
      const sid = String(sessionId || "").trim();
      if (!sid) return "";
      const map = readLocalSessionTitles();
      return String(map[sid] || "").trim();
    }

    function ensureLocalActiveSessionPresent() {
      const sid = String(activeSessionId || sessionIdEl.value || "").trim();
      if (!sid) return;
      const exists = sessionCache.some((item) => item.session_id === sid);
      if (exists) return;

      sessionCache.unshift({
        session_id: sid,
        title: getLocalSessionTitle(sid) || "New Chat",
        message_count: 0,
        last_message_at: new Date().toISOString(),
      });
    }

    function setSessionSyncState(state) {
      const normalized = ["syncing", "saved", "error"].includes(state) ? state : "saved";
      sessionSyncState = normalized;

      syncIndicatorEl.classList.remove("syncing", "saved", "error");
      syncIndicatorEl.classList.add(normalized);
      syncIndicatorEl.textContent = normalized === "syncing"
        ? "Syncing"
        : normalized === "error"
          ? "Not Saved"
          : "Saved";

      renderSessionList(sessionCache);
    }

    function isNewChatTitle(title) {
      const value = String(title || "").trim().toLowerCase();
      return !value || value === "new chat";
    }

    function mergeSessionItems(serverItems) {
      const server = Array.isArray(serverItems) ? serverItems.slice() : [];
      if (!sessionCache.length) return server;

      const localMap = new Map(sessionCache.map((item) => [item.session_id, item]));
      const merged = server.map((row) => {
        const local = localMap.get(row.session_id);
        const localStoredTitle = getLocalSessionTitle(row.session_id);
        if (!local) return row;

        // Preserve local generated title while server still has placeholder title.
        const candidateLocal = localStoredTitle || local.title;
        const nextTitle = isNewChatTitle(row.title) && !isNewChatTitle(candidateLocal)
          ? candidateLocal
          : row.title;

        return {
          ...row,
          title: nextTitle,
        };
      });

      // Keep local-only sessions (created locally before server roundtrip) visible.
      const seen = new Set(merged.map((item) => item.session_id));
      sessionCache.forEach((item) => {
        if (!seen.has(item.session_id)) {
          merged.unshift(item);
        }
      });

      return merged;
    }

    function applyLocalSessionTitle(sessionId, prompt) {
      const title = generateTitleFromPrompt(prompt);
      const nowIso = new Date().toISOString();
      const targetId = String(sessionId || "").trim();
      if (!targetId) return;
      saveLocalSessionTitle(targetId, title);

      let found = false;
      sessionCache = (sessionCache || []).map((item) => {
        if (item.session_id !== targetId) return item;
        found = true;
        const msgCount = Number(item.message_count || 0);
        const oldTitle = String(item.title || "").trim().toLowerCase();
        const shouldReplace = msgCount <= 1 || !oldTitle || oldTitle === "new chat";
        const nextTitle = shouldReplace ? title : item.title;
        return {
          ...item,
          title: nextTitle,
          last_message_at: nowIso,
          message_count: msgCount + 1,
        };
      });

      if (!found) {
        sessionCache.unshift({
          session_id: targetId,
          title,
          last_message_at: nowIso,
          message_count: 1,
        });
      }

      renderSessionList(sessionCache);
    }

    function renderSessionList(items) {
      sessionCache = Array.isArray(items) ? items.slice() : [];
      sessionListEl.innerHTML = "";

      if (!items || !items.length) {
        const li = document.createElement("li");
        li.className = "session-item";
        li.innerHTML = '<div class="session-item-title">No sessions found. New session has been created.</div>';
        sessionListEl.appendChild(li);
        return;
      }

      sessionCache.forEach((item) => {
        const sessionId = String(item.session_id || "").trim();
        const li = document.createElement("li");
        li.className = "session-item" + (sessionId === activeSessionId ? " active" : "");

        const row = document.createElement("div");
        row.className = "session-item-row";

        const title = document.createElement("div");
        title.className = "session-item-title";
        title.textContent = item.title || sessionId;

        const menu = document.createElement("button");
        menu.type = "button";
        menu.className = "session-item-menu";
        menu.textContent = "...";
        menu.addEventListener("click", (event) => {
          // Reserved for future actions (rename/delete).
          event.stopPropagation();
        });

        row.appendChild(title);
        row.appendChild(menu);

        const meta = document.createElement("div");
        meta.className = "session-item-meta";
        if (sessionId === activeSessionId && sessionSyncState === "syncing") {
          meta.textContent = "syncing...";
        } else if (sessionId === activeSessionId && sessionSyncState === "error") {
          meta.textContent = "not saved";
        } else {
          meta.textContent = `${item.message_count || 0} messages`;
        }

        li.appendChild(row);
        li.appendChild(meta);
        li.addEventListener("click", async () => {
          await selectSession(sessionId, true);
        });
        sessionListEl.appendChild(li);
      });
    }

    async function loadSessions() {
      const apiBase = normalizeBaseUrl(apiBaseEl.value) || defaultApiBase;
      try {
        const response = await fetch(`${apiBase}/memory-sessions?limit=80`);
        if (!response.ok) {
          ensureLocalActiveSessionPresent();
          renderSessionList(sessionCache);
          return;
        }
        const payload = await response.json();
        const items = mergeSessionItems(payload.items || []);
        if (!items.length) {
          const bootSession = sessionIdEl.value.trim() || activeSessionId || createSessionId();
          await ensureSessionExists(bootSession, "New Chat");
          const retry = await fetch(`${apiBase}/memory-sessions?limit=80`);
          if (retry.ok) {
            const nextPayload = await retry.json();
            renderSessionList(mergeSessionItems(nextPayload.items || []));
            return;
          }
        }
        renderSessionList(items);
      } catch (err) {
        ensureLocalActiveSessionPresent();
        renderSessionList(sessionCache);
      }
    }

    async function ensureSessionExists(sessionId, title) {
      const apiBase = normalizeBaseUrl(apiBaseEl.value) || defaultApiBase;
      try {
        await fetch(`${apiBase}/memory-sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            title: title || "New Chat",
          }),
        });
      } catch (err) {
        // Keep UI flow working even if session bootstrap fails.
      }
    }

    function upsertSessionTitle(sessionId, title) {
      const sid = String(sessionId || "").trim();
      const ttl = String(title || "").trim();
      if (!sid || !ttl) return;

      let found = false;
      sessionCache = (sessionCache || []).map((item) => {
        if (item.session_id !== sid) return item;
        found = true;
        return { ...item, title: ttl };
      });

      if (!found) {
        sessionCache.unshift({
          session_id: sid,
          title: ttl,
          message_count: 0,
          last_message_at: new Date().toISOString(),
        });
      }

      renderSessionList(sessionCache);
    }

    async function requestAiSessionTitle(sessionId, prompt) {
      const apiBase = normalizeBaseUrl(apiBaseEl.value) || defaultApiBase;
      const response = await fetch(`${apiBase}/memory-sessions/title`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, prompt }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate session title");
      }

      const payload = await response.json();
      const aiTitle = String(payload.title || "").trim();
      if (aiTitle) {
        upsertSessionTitle(sessionId, aiTitle);
      }
      return aiTitle;
    }

    function renderMessageFromMemory(item) {
      const role = String(item?.role || "assistant").toLowerCase();
      const content = String(item?.content || "");
      if (!content.trim()) return;

      if (role === "user") {
        addTextBubble(content, "user");
        return;
      }

      const parsedCard = tryParseCardFromText(content);
      if (parsedCard) {
        addCard(parsedCard);
        return;
      }

      const imageUrls = extractImageUrls(content);
      if (imageUrls.length) {
        imageUrls.forEach((url) => {
          const caption = /staticmap/i.test(url) ? "Static map" : "Travel image";
          addImageBubble(url, caption);
        });
        return;
      }

      addRichTextBubble(content);
    }

    async function loadSessionConversation(sessionId) {
      const apiBase = normalizeBaseUrl(apiBaseEl.value) || defaultApiBase;
      chatEl.innerHTML = "";

      try {
        const response = await fetch(`${apiBase}/memory/${encodeURIComponent(sessionId)}?limit=200`);
        if (!response.ok) {
          addTextBubble("Could not load this session history.", "agent");
          return;
        }
        const payload = await response.json();
        const items = payload.items || [];

        if (!items.length) {
          addTextBubble("This is a new session. Start chatting.", "agent");
          return;
        }

        let renderedCount = 0;
        items.forEach((item) => {
          try {
            renderMessageFromMemory(item);
            renderedCount += 1;
          } catch (err) {
            // Skip malformed history item and continue rendering the rest.
          }
        });

        setStatus(`Loaded ${renderedCount} messages from this session`);
      } catch (err) {
        addTextBubble("Could not load this session history.", "agent");
      }
    }

    async function selectSession(sessionId, loadConversation) {
      const selected = String(sessionId || "").trim() || createSessionId();
      activeSessionId = selected;
      sessionIdEl.value = selected;
      await ensureSessionExists(selected, "New Chat");

      if (loadConversation) {
        await loadSessionConversation(selected);
      }

      await loadSessions();
    }

    function scrollToBottom() {
      chatEl.scrollTop = chatEl.scrollHeight;
    }

    function addTextBubble(text, role) {
      const bubble = document.createElement("article");
      bubble.className = "bubble " + role;
      bubble.textContent = text;
      chatEl.appendChild(bubble);
      scrollToBottom();
    }

    function escapeHtml(text) {
      return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function formatInline(text) {
      return text
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/`([^`]+)`/g, "<code>$1</code>");
    }

    function markdownToSafeHtml(text) {
      const source = escapeHtml(text || "").replace(/\r\n/g, "\n");
      const lines = source.split("\n");
      const html = [];
      let inUl = false;
      let inOl = false;

      const closeLists = () => {
        if (inUl) {
          html.push("</ul>");
          inUl = false;
        }
        if (inOl) {
          html.push("</ol>");
          inOl = false;
        }
      };

      lines.forEach((raw) => {
        const line = raw.trim();
        if (!line) {
          closeLists();
          return;
        }

        if (line.startsWith("### ")) {
          closeLists();
          html.push(`<h4>${formatInline(line.slice(4))}</h4>`);
          return;
        }

        if (line.startsWith("## ") || line.startsWith("# ")) {
          closeLists();
          const offset = line.startsWith("## ") ? 3 : 2;
          html.push(`<h3>${formatInline(line.slice(offset))}</h3>`);
          return;
        }

        if (/^[-*]\s+/.test(line)) {
          if (!inUl) {
            closeLists();
            html.push("<ul>");
            inUl = true;
          }
          html.push(`<li>${formatInline(line.replace(/^[-*]\s+/, ""))}</li>`);
          return;
        }

        if (/^\d+\.\s+/.test(line)) {
          if (!inOl) {
            closeLists();
            html.push("<ol>");
            inOl = true;
          }
          html.push(`<li>${formatInline(line.replace(/^\d+\.\s+/, ""))}</li>`);
          return;
        }

        closeLists();
        html.push(`<p>${formatInline(line)}</p>`);
      });

      closeLists();
      return html.join("");
    }

    function addRichTextBubble(text) {
      const bubble = document.createElement("article");
      bubble.className = "bubble agent rich";
      bubble.innerHTML = markdownToSafeHtml(text);
      chatEl.appendChild(bubble);
      scrollToBottom();
    }

    function createStreamingAssistantBubble() {
      const bubble = document.createElement("article");
      bubble.className = "bubble agent";
      bubble.textContent = "";
      chatEl.appendChild(bubble);
      scrollToBottom();
      return bubble;
    }

    function appendStreamingToken(bubble, token) {
      bubble.textContent += token;
      scrollToBottom();
    }

    function finalizeStreamingBubble(bubble) {
      const fullText = bubble.textContent || "";
      bubble.className = "bubble agent rich";
      bubble.innerHTML = markdownToSafeHtml(fullText);
      scrollToBottom();
    }

    function addImageBubble(url, caption) {
      const figure = document.createElement("figure");
      figure.className = "bubble-image";

      const img = document.createElement("img");
      img.src = url;
      img.alt = caption || "Shared travel image";
      figure.appendChild(img);

      if (caption) {
        const cap = document.createElement("figcaption");
        cap.textContent = caption;
        figure.appendChild(cap);
      }

      chatEl.appendChild(figure);
      scrollToBottom();
    }

    function normalizeCardPayload(raw) {
      if (typeof raw === "string") {
        try {
          const parsed = JSON.parse(raw);
          return normalizeCardPayload(parsed);
        } catch (err) {
          return null;
        }
      }

      if (!raw || typeof raw !== "object") return null;

      if (raw.trip) {
        return {
          trip: raw.trip,
          details: raw.details || {},
        };
      }
      if (raw.type === "card" && raw.data) {
        return normalizeCardPayload(raw.data);
      }
      if (raw.data && typeof raw.data === "object") {
        return normalizeCardPayload(raw.data);
      }

      if (raw.data && typeof raw.data === "string") {
        try {
          return normalizeCardPayload(JSON.parse(raw.data));
        } catch (err) {
          return null;
        }
      }

      return null;
    }

    function extractImageUrls(text) {
      if (!text || typeof text !== "string") return [];
      const urls = new Set();

      const mdRegex = /!\[[^\]]*\]\((https?:\/\/[^\s)]+)\)/g;
      let m;
      while ((m = mdRegex.exec(text)) !== null) {
        urls.add(m[1]);
      }

      const urlRegex = /(https?:\/\/[^\s"'<>]+(?:\.png|\.jpg|\.jpeg|\.gif|\.webp)(?:\?[^\s"'<>]*)?|https?:\/\/maps\.googleapis\.com\/maps\/api\/staticmap[^\s"'<>]*)/gi;
      let u;
      while ((u = urlRegex.exec(text)) !== null) {
        urls.add(u[1]);
      }

      return Array.from(urls);
    }

    function tryParseCardFromText(text) {
      if (!text || typeof text !== "string") return null;

      // 1) Parse fenced json block anywhere in the response.
      const codeBlockMatch = text.match(/```json\s*([\s\S]*?)```/i);
      if (codeBlockMatch && codeBlockMatch[1]) {
        try {
          const parsed = JSON.parse(codeBlockMatch[1].trim());
          const normalized = normalizeCardPayload(parsed);
          if (normalized) return normalized;
        } catch (err) {
          // fall through
        }
      }

      // 2) Parse raw full JSON text.
      const cleaned = text.trim();
      if (cleaned.startsWith("{") && cleaned.endsWith("}")) {
        try {
          const parsed = JSON.parse(cleaned);
          const normalized = normalizeCardPayload(parsed);
          if (normalized) return normalized;
        } catch (err) {
          // fall through
        }
      }

      // 3) Parse first JSON object-looking fragment between braces.
      const start = text.indexOf("{");
      const end = text.lastIndexOf("}");
      if (start !== -1 && end > start) {
        const fragment = text.slice(start, end + 1).trim();
        try {
          const parsed = JSON.parse(fragment);
          const normalized = normalizeCardPayload(parsed);
          if (normalized) return normalized;
        } catch (err) {
          return null;
        }
      }

      return null;
    }

    function el(tag, cls, text) {
      const node = document.createElement(tag);
      if (cls) node.className = cls;
      if (text !== undefined) node.textContent = text;
      return node;
    }

    function buildDetailsContent(data) {
      const trip = data?.trip || {};
      const details = data?.details || {};
      const destination = trip.destination || trip.title || "Destination";

      const wrapper = el("section", "card-details open");

      if (details?.static_map?.image_url) {
        const mapImg = document.createElement("img");
        mapImg.className = "detail-map";
        mapImg.src = details.static_map.image_url;
        mapImg.alt = details.static_map.description || "Trip map";
        wrapper.appendChild(mapImg);
      }

      wrapper.appendChild(el("h3", "detail-title", trip.title || `${destination} Itinerary`));
      wrapper.appendChild(el("p", "detail-subtitle", "Detailed day by day travel plan"));

      if (trip.description) {
        wrapper.appendChild(el("p", "card-desc", trip.description));
      }

      if (Array.isArray(trip.categories) && trip.categories.length) {
        wrapper.appendChild(el("h4", "detail-section-title", "Categories"));
        const catList = el("ul", "detail-bullets");
        trip.categories.forEach((category) => {
          catList.appendChild(el("li", "", String(category)));
        });
        wrapper.appendChild(catList);
      }

      if (Array.isArray(trip.summary_itinerary) && trip.summary_itinerary.length) {
        wrapper.appendChild(el("h4", "detail-section-title", "Summary Itinerary"));
        const summaryList = el("ul", "detail-bullets");
        trip.summary_itinerary.forEach((item) => {
          const title = `${item?.day || "Day"}: ${item?.title || "Plan"}`;
          summaryList.appendChild(el("li", "", title));

          if (Array.isArray(item?.activities) && item.activities.length) {
            item.activities.forEach((activity) => {
              summaryList.appendChild(el("li", "", `- ${activity}`));
            });
          }
        });
        wrapper.appendChild(summaryList);
      }

      if (Array.isArray(details.tour_spots) && details.tour_spots.length) {
        wrapper.appendChild(el("h4", "detail-section-title", details.tour_spots_title || "Major Tour Spots"));
        const spotsList = el("ul", "detail-bullets");
        details.tour_spots.forEach((spot) => {
          spotsList.appendChild(el("li", "", String(spot)));
        });
        wrapper.appendChild(spotsList);
      }

      let hasDetailBlocks = false;

      if (Array.isArray(details.days) && details.days.length) {
        hasDetailBlocks = true;
        details.days.forEach((dayData) => {
          const dayCard = el("article", "day-card");
          dayCard.appendChild(el("h4", "day-title", `${dayData.day}: ${dayData.title}`));

          if (dayData.image_url) {
            const dayImage = document.createElement("img");
            dayImage.className = "day-image";
            dayImage.src = dayData.image_url;
            dayImage.alt = `${dayData.day} image`;
            dayCard.appendChild(dayImage);
          }

          const dayList = el("ul", "day-list");
          if (Array.isArray(dayData.schedule)) {
            dayData.schedule.forEach((item) => {
              const li = el("li");
              const time = item.time || "Slot";
              li.appendChild(el("span", "day-time", `${time}:`));
              li.appendChild(el("span", "", item.description || ""));
              dayList.appendChild(li);
            });
          }
          dayCard.appendChild(dayList);
          wrapper.appendChild(dayCard);
        });
      } else if (Array.isArray(trip.summary_itinerary) && trip.summary_itinerary.length) {
        hasDetailBlocks = true;
        // Fallback when detailed day schedules are not provided.
        trip.summary_itinerary.forEach((item) => {
          const dayCard = el("article", "day-card");
          dayCard.appendChild(el("h4", "day-title", `${item?.day || "Day"}: ${item?.title || "Plan"}`));
          const dayList = el("ul", "day-list");
          (item?.activities || []).forEach((activity) => {
            const li = el("li");
            li.appendChild(el("span", "day-time", "Note:"));
            li.appendChild(el("span", "", String(activity)));
            dayList.appendChild(li);
          });
          dayCard.appendChild(dayList);
          wrapper.appendChild(dayCard);
        });
      }

      if (!hasDetailBlocks) {
        wrapper.appendChild(el("p", "card-desc", "No detailed itinerary provided for this card yet."));
      }

      return wrapper;
    }

    function openDetailsModal(data) {
      const trip = data?.trip || {};
      detailsModalTitleEl.textContent = trip.title || "Trip Details";
      detailsModalBodyEl.innerHTML = "";
      detailsModalBodyEl.appendChild(buildDetailsContent(data));
      detailsModalOverlayEl.classList.add("open");
      document.body.style.overflow = "hidden";
    }

    function closeDetailsModal() {
      detailsModalOverlayEl.classList.remove("open");
      document.body.style.overflow = "auto";
    }

    function createCard(data) {
      const trip = data?.trip || {};
      const details = data?.details || {};
      const destination = trip.destination || trip.title || "Destination";
      const description = trip.description || "Explore scenic drives, local food, and unforgettable views.";
      const imageUrl = trip.image_url || "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80";
      const categories = Array.isArray(trip.categories) && trip.categories.length
        ? trip.categories.slice(0, 4)
        : ["Beach", "Nature", "Food"];

      let summary = [];
      if (Array.isArray(trip.summary_itinerary) && trip.summary_itinerary.length) {
        summary = trip.summary_itinerary.slice(0, 4).map((item) => {
          const d = item?.day || "Day";
          const t = item?.title || item?.activities?.[0] || "Plan";
          return `${d}: ${t}`;
        });
      } else if (Array.isArray(details.days) && details.days.length) {
        summary = details.days.slice(0, 4).map((d) => `${d.day || "Day"}: ${d.title || "Plan"}`);
      } else if (Array.isArray(details.tour_spots) && details.tour_spots.length) {
        summary = details.tour_spots.slice(0, 4).map((s, i) => `Spot ${i + 1}: ${s}`);
      }

      if (!summary.length) {
        summary = [
          "Day 1: Beach & Chill",
          "Day 2: Nature & Adventure",
          "Day 3: Local & Leisure",
        ];
      }

      const card = el("article", "card");
      const content = el("section", "card-content");
      const compact = el("section", "card-compact");

      const img = document.createElement("img");
      img.className = "card-image";
      img.src = imageUrl;
      img.alt = trip.title || "Trip image";
      compact.appendChild(img);

      const titleRow = el("div", "card-title-row");
      titleRow.appendChild(el("span", "card-logo", "AI"));
      titleRow.appendChild(el("h3", "card-title", `${destination} 3-Day Getaway`));
      compact.appendChild(titleRow);

      const days = trip?.duration?.days ?? 3;
      const nights = trip?.duration?.nights ?? 2;
      const spotsCount = trip?.spots_count ?? (Array.isArray(details?.tour_spots) ? details.tour_spots.length : 6);

      const meta = el("div", "card-meta");
      meta.appendChild(el("span", "", `${days} days - ${nights} nights`));
      meta.appendChild(el("span", "card-meta-dot", "|"));
      meta.appendChild(el("span", "", `${spotsCount} Spots`));
      compact.appendChild(meta);

      const catRow = el("div", "card-cats");
      categories.forEach((c) => catRow.appendChild(el("span", "card-cat", c)));
      compact.appendChild(catRow);

      compact.appendChild(el("p", "card-desc", description));

      if (Array.isArray(details.tour_spots) && details.tour_spots.length) {
        compact.appendChild(el("p", "card-desc", `Top spots: ${details.tour_spots.slice(0, 3).join(", ")}`));
      }

      const list = el("ul", "card-list");
      summary.forEach((line) => {
        const li = el("li");
        li.appendChild(el("span", "check", "v"));
        li.appendChild(el("span", "", line));
        list.appendChild(li);
      });
      compact.appendChild(list);

      const detailsBtn = el("button", "card-primary", "View Details");
      detailsBtn.type = "button";
      compact.appendChild(detailsBtn);

      detailsBtn.addEventListener("click", () => {
        openDetailsModal(data);
      });

      content.appendChild(compact);

      card.appendChild(content);

      const regen = el("section", "regen-wrap");
      regen.appendChild(el("p", "regen-title", "Not satisfied with this plan?"));
      const regenBtn = el("button", "regen-btn", "Refresh Plan");
      regenBtn.type = "button";
      regenBtn.addEventListener("click", () => {
        const target = trip.destination || destination;
        promptEl.value = `Regenerate a different 3-day plan for ${target}`;
        promptEl.focus();
      });
      regen.appendChild(regenBtn);
      card.appendChild(regen);

      return card;
    }

    function addCard(data) {
      const card = createCard(data);
      chatEl.appendChild(card);
      scrollToBottom();
    }

    function normalizeBaseUrl(base) {
      return String(base || "").trim().replace(/\/$/, "");
    }

    function buildApiCandidates(preferredBase) {
      const candidates = [];
      const seen = new Set();

      const add = (value) => {
        const normalized = normalizeBaseUrl(value);
        if (!normalized || seen.has(normalized)) return;
        seen.add(normalized);
        candidates.push(normalized);
      };

      add(preferredBase);
      add("http://127.0.0.1:8000");
      add("http://localhost:8000");

      // Helpful when API is bound to a LAN IP and UI is opened from that host.
      if (
        /^https?:$/i.test(window.location.protocol) &&
        window.location.hostname &&
        !["localhost", "127.0.0.1"].includes(window.location.hostname)
      ) {
        add(`${window.location.protocol}//${window.location.hostname}:8000`);
      }

      return candidates;
    }

    async function streamChatWithFallback(prompt, sessionId, onEvent) {
      const preferredBase = normalizeBaseUrl(apiBaseEl.value) || defaultApiBase;
      const apiCandidates = buildApiCandidates(preferredBase);
      let lastError = null;

      for (const apiBase of apiCandidates) {
        try {
          const response = await fetch(`${apiBase}/chat/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt, session_id: sessionId }),
          });

          if (!response.ok || !response.body) {
            const errText = await response.text();
            if (response.status === 404 || response.status === 405) {
              lastError = new Error(`API ${response.status}: ${errText}`);
              continue;
            }
            throw new Error(`API ${response.status}: ${errText}`);
          }

          apiBaseEl.value = apiBase;
          const reader = response.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let buffer = "";

          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const events = buffer.split("\n\n");
            buffer = events.pop() || "";

            for (const evt of events) {
              const dataLine = evt
                .split("\n")
                .find((line) => line.startsWith("data: "));
              if (!dataLine) continue;

              const raw = dataLine.slice(6);
              let parsed;
              try {
                parsed = JSON.parse(raw);
              } catch (err) {
                continue;
              }

              onEvent(parsed);
            }
          }

          return;
        } catch (err) {
          if (err && err.name === "TypeError") {
            lastError = err;
            continue;
          }
          lastError = err;
          break;
        }
      }

      throw (
        lastError ||
        new Error("Could not reach API stream. Ensure backend is running on http://127.0.0.1:8000")
      );
    }

    async function sendPrompt(prompt) {
      const sessionId = sessionIdEl.value.trim() || activeSessionId || "user-session-1";
      activeSessionId = sessionId;

      setSessionSyncState("syncing");
      setStatus("Thinking...");
      const wantsImage = /photo|image|map|static map|picture|pic/i.test(prompt);
      let streamBubble = null;
      let streamDone = false;
      let cardRendered = false;

      await streamChatWithFallback(prompt, sessionId, (evt) => {
        if (evt.type === "token") {
          if (!streamBubble) {
            streamBubble = createStreamingAssistantBubble();
          }
          appendStreamingToken(streamBubble, String(evt.data || ""));
          return;
        }

        if (evt.type === "card") {
          const cardData = normalizeCardPayload(evt.data);
          if (cardData) {
            if (streamBubble) {
              streamBubble.remove();
              streamBubble = null;
            }
            addCard(cardData);
            cardRendered = true;
          }
          return;
        }

        if (evt.type === "done") {
          streamDone = true;
          return;
        }

        if (evt.type === "error") {
          throw new Error(String(evt.data || "Streaming error"));
        }
      });

      if (streamBubble && !cardRendered) {
        const textData = streamBubble.textContent || "";

        const parsedCard = tryParseCardFromText(textData);
        if (parsedCard) {
          streamBubble.remove();
          addCard(parsedCard);
          cardRendered = true;
        }

        if (cardRendered) {
          // Card has already been rendered from streamed JSON text.
        } else {
        const imageUrls = extractImageUrls(textData);
        if (wantsImage && imageUrls.length) {
          streamBubble.remove();
          imageUrls.forEach((url) => {
            const caption = /staticmap/i.test(url) ? "Static map" : "Travel image";
            addImageBubble(url, caption);
          });
        } else {
          finalizeStreamingBubble(streamBubble);
        }
        }
      }

      if (!streamDone) {
        setStatus("Waiting for stream...");
      }

      await loadSessions();
      setSessionSyncState("saved");

      setStatus("Ready");
    }

    newSessionEl.addEventListener("click", async () => {
      const newId = createSessionId();
      await ensureSessionExists(newId, "New Chat");
      chatEl.innerHTML = "";
      addTextBubble("New session started. Ask anything about travel.", "agent");
      await selectSession(newId, false);
      setSessionSyncState("saved");
    });

    detailsModalCloseEl.addEventListener("click", () => {
      closeDetailsModal();
    });

    detailsModalOverlayEl.addEventListener("click", (event) => {
      if (event.target === detailsModalOverlayEl) {
        closeDetailsModal();
      }
    });

    sessionIdEl.addEventListener("change", async () => {
      await selectSession(sessionIdEl.value, true);
    });

    formEl.addEventListener("submit", async (event) => {
      event.preventDefault();
      const prompt = promptEl.value.trim();
      if (!prompt) return;

      sendBtnEl.disabled = true;
      promptEl.disabled = true;

      const currentSession = sessionIdEl.value.trim() || activeSessionId || "user-session-1";
      activeSessionId = currentSession;
      sessionIdEl.value = currentSession;

      requestAiSessionTitle(currentSession, prompt)
        .catch(() => {
          // Keep chat usable if title generation fails.
        });

      addTextBubble(prompt, "user");
      promptEl.value = "";
      autoResizePrompt();

      try {
        await sendPrompt(prompt);
      } catch (error) {
        setSessionSyncState("error");
        setStatus("Error");
        addTextBubble(`Error: ${error.message}`, "agent");
      } finally {
        promptEl.disabled = false;
        sendBtnEl.disabled = false;
        promptEl.focus();
      }
    });

    promptEl.addEventListener("input", autoResizePrompt);
    promptEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        formEl.requestSubmit();
      }
    });

    addTextBubble("Welcome. Ask normal questions for text replies, or ask for an itinerary to get a travel card.", "agent");
    selectSession(activeSessionId, false);
    autoResizePrompt();
    setStatus("Ready");
