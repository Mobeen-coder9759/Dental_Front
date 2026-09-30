"""Antigravity-style interactive particle background for the whole Streamlit app.

Call `inject_particle_background()` once per page run. ui.inject_global_css()
already does this, so every page that injects the global CSS gets the effect.

How it works
------------
Streamlit runs custom JS inside a sandboxed iframe, so this script reaches out
to the parent page, adds a fixed full-screen <canvas> behind the app, and makes
the app's own containers transparent so the particles show through everywhere
(main area, sidebar, login screen, every page).

Tweak the look in the CONFIG block inside _SCRIPT below.
"""

import hashlib

import streamlit.components.v1 as components

# Page background behind the particles (matches the dashboard's dark theme).
PAGE_BACKGROUND = "#0F1117"

_SCRIPT = r"""
<script>
(() => {
    const VERSION = "__VERSION__";
    const PAGE_BG = "__PAGE_BG__";

    const parentDoc = window.parent.document;
    const parentWin = window.parent;

    // Streamlit reruns this component on every interaction. If the exact same
    // version is already running, leave it alone so the particles never reset
    // or flicker. If the code changed, tear the old one down and rebuild.
    const existing = parentWin.__antigravityParticleField;
    if (existing && existing.version === VERSION
        && parentDoc.getElementById("antigravity-particle-canvas")) {
        return;
    }
    if (existing?.destroy) existing.destroy();

    const oldCanvas = parentDoc.getElementById("antigravity-particle-canvas");
    if (oldCanvas) oldCanvas.remove();
    const oldStyle = parentDoc.getElementById("antigravity-particle-style");
    if (oldStyle) oldStyle.remove();

    const CONFIG = {
        // ── Amount ──────────────────────────────────────────────────────
        desktopParticles: 540,
        mobileParticles: 280,
        canvasOpacity: 0.95,    // overall strength. Lower it if it distracts from data

        // ── Ring shape (the empty middle keeps content readable) ────────
        innerRadius: 0.30,
        outerRadius: 1.03,
        ringParticleShare: 0.88,
        radiusXArea: 0.53,      // ring width  as a fraction of the main content area
        radiusYViewport: 0.58,  // ring height as a fraction of the viewport
        maxRadiusX: 760,
        maxRadiusY: 470,
        centerYRatio: 0.50,

        // ── Particle look ───────────────────────────────────────────────
        minLength: 1.6,
        maxLength: 3.8,
        minAlpha: 0.50,
        maxAlpha: 1.00,
        lineWidth: 1.6,

        // ── Ambient flow ────────────────────────────────────────────────
        driftX: 34,
        driftY: 26,
        flowStrength: 30,
        flowSpeed: 0.00045,

        // ── Cursor interaction: particles revolve around the cursor ─────
        mouseRadius: 170,       // particles whose home spot is inside this get caught
        mouseRelease: 1.25,     // they let go once their home is farther than mouseRadius * this
        spiralIdleMs: 1200,     // cursor still for this long -> spiral dissolves (0 = never)
        spiralRadius: 115,      // size of the finished spiral (px)
        spiralCore: 18,         // empty hole at the center (px)
        spiralArms: 3,          // number of spiral arms
        spiralTwist: 0.017,     // curl of the arms (radians per px). 0 = straight rays
        spiralSpin: 0.0006,     // revolution speed of the spiral
        spiralDir: 1,           // 1 = clockwise, -1 = counter-clockwise
        spiralArmWidth: 0.10,   // arm thickness (radians). Lower = sharper lines
        spiralGrabSpeed: 0.07,  // how fast particles fly into / out of the spiral (0-1)
        spiralSnap: 1.0,        // extra spring strength inside the spiral

        // ── Spring physics (tuned for 60fps, scaled automatically) ──────
        springStrength: 0.040,
        friction: 0.865,

        // Brightened Antigravity palette so it glows on the dark page.
        colors: [
            "#4C82FF",
            "#6B80FF",
            "#8B73F0",
            "#A67BE8",
            "#D05FC0",
            "#F0648E",
            "#F58466",
            "#F5B84A"
        ],

        // Faint static dust across the whole viewport.
        dustDensity: 0.00014,   // dots per px^2
        dustMinAlpha: 0.12,
        dustMaxAlpha: 0.32,
        dustMinR: 0.6,
        dustMaxR: 1.3,
        dustColor: "#7C86A6"
    };

    const reducedMotion = !!parentWin.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) {
        CONFIG.driftX *= 0.2;
        CONFIG.driftY *= 0.2;
        CONFIG.flowStrength *= 0.2;
    }

    // Make the whole Streamlit app see-through so the canvas shows on every
    // page, including the login screen and the sidebar.
    const style = parentDoc.createElement("style");
    style.id = "antigravity-particle-style";
    style.textContent = `
        html, body {
            background: ${PAGE_BG} !important;
        }
        .stApp,
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stBottom"],
        [data-testid="stBottomBlockContainer"],
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        [data-testid="stAppViewContainer"] > section,
        [data-testid="stHeader"],
        [data-testid="stToolbar"] {
            position: relative;
            z-index: 2;
        }
        /* Frosted sidebar: particles drift behind it, text stays readable. */
        [data-testid="stSidebar"] {
            background: rgba(19, 21, 31, 0.62) !important;
            -webkit-backdrop-filter: blur(10px);
            backdrop-filter: blur(10px);
        }
        [data-testid="stSidebarContent"] {
            background: transparent !important;
        }
        #antigravity-particle-canvas {
            position: fixed;
            inset: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 0;
            opacity: ${CONFIG.canvasOpacity};
        }
    `;
    parentDoc.head.appendChild(style);

    const canvas = parentDoc.createElement("canvas");
    canvas.id = "antigravity-particle-canvas";
    canvas.setAttribute("aria-hidden", "true");
    parentDoc.body.insertBefore(canvas, parentDoc.body.firstChild);

    const ctx = canvas.getContext("2d", { alpha: true });

    let width = 0;
    let height = 0;
    let dpr = 1;
    let centerX = 0;
    let centerY = 0;
    let radiusX = 0;
    let radiusY = 0;
    let particles = [];
    let dustLayer = null;
    let rafId = null;
    let destroyed = false;
    let lastTime = null;
    let frame = 0;

    const mouse = { x: -10000, y: -10000, active: false, lastMove: 0 };

    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    const rand = (a, b) => a + Math.random() * (b - a);

    // The ring is centered on the main content area (not the whole window),
    // so it stays behind the page content when the sidebar is open.
    function getArea() {
        const main = parentDoc.querySelector('[data-testid="stMain"]')
            || parentDoc.querySelector("section.main");
        if (main) {
            const r = main.getBoundingClientRect();
            if (r.width > 200) return { cx: r.left + r.width / 2, w: r.width };
        }
        return { cx: parentWin.innerWidth * 0.5, w: parentWin.innerWidth };
    }

    function resizeCanvas() {
        dpr = Math.min(parentWin.devicePixelRatio || 1, 2);
        width = parentWin.innerWidth;
        height = parentWin.innerHeight;

        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;

        const area = getArea();
        centerX = area.cx;
        centerY = height * CONFIG.centerYRatio;
        radiusX = Math.min(area.w * CONFIG.radiusXArea, CONFIG.maxRadiusX);
        radiusY = Math.min(height * CONFIG.radiusYViewport, CONFIG.maxRadiusY);
    }

    // When the sidebar opens/closes the content area moves. Slide every
    // particle's home spot with it so the ring glides instead of jumping.
    function recenter() {
        const dx = getArea().cx - centerX;
        if (Math.abs(dx) < 0.5) return;
        centerX += dx;
        for (const p of particles) p.homeX += dx;
    }

    function randomRingAnchor() {
        const theta = Math.random() * Math.PI * 2;

        // Area-uniform sampling in an annulus, biased slightly to the middle band.
        const u = Math.pow(Math.random(), 0.82);
        const inner2 = CONFIG.innerRadius * CONFIG.innerRadius;
        const outer2 = CONFIG.outerRadius * CONFIG.outerRadius;
        const r = Math.sqrt(inner2 + u * (outer2 - inner2));

        const wobble = rand(0.93, 1.08);
        return {
            x: centerX + Math.cos(theta) * radiusX * r * wobble,
            y: centerY + Math.sin(theta) * radiusY * r / wobble,
            theta,
            normalizedRadius: r
        };
    }

    function randomOuterAnchor() {
        // A few particles live outside the ring so the field fades toward the edges.
        for (let tries = 0; tries < 30; tries++) {
            const x = Math.random() * width;
            const y = Math.random() * height;
            const nx = (x - centerX) / Math.max(radiusX, 1);
            const ny = (y - centerY) / Math.max(radiusY, 1);
            const ellipticalDistance = Math.sqrt(nx * nx + ny * ny);
            if (ellipticalDistance > CONFIG.innerRadius * 1.15) {
                return { x, y, theta: Math.atan2(ny, nx), normalizedRadius: ellipticalDistance };
            }
        }
        return randomRingAnchor();
    }

    class Particle {
        constructor(index, count) {
            const anchor = Math.random() < CONFIG.ringParticleShare
                ? randomRingAnchor()
                : randomOuterAnchor();

            this.homeX = anchor.x;
            this.homeY = anchor.y;
            this.x = this.homeX + rand(-2, 2);
            this.y = this.homeY + rand(-2, 2);
            this.vx = 0;
            this.vy = 0;

            this.phase = Math.random() * Math.PI * 2;
            this.phase2 = Math.random() * Math.PI * 2;
            this.speed = rand(0.70, 1.35);
            this.wander = rand(0.55, 1.35);
            this.length = rand(CONFIG.minLength, CONFIG.maxLength);
            this.alpha = rand(CONFIG.minAlpha, CONFIG.maxAlpha);
            this.angle = anchor.theta + Math.PI / 2;

            // Spiral membership: which arm, where along it, plus a tiny
            // sideways offset so each arm has some thickness.
            this.arm = Math.floor(Math.random() * CONFIG.spiralArms);
            this.armT = Math.random();
            this.armJitter = rand(-1, 1) * CONFIG.spiralArmWidth;
            this.grab = 0;
            this.captured = false;

            const paletteOffset = Math.floor(Math.random() * CONFIG.colors.length);
            const paletteIndex = (Math.floor((index / Math.max(count, 1)) * CONFIG.colors.length * 2)
                + paletteOffset) % CONFIG.colors.length;
            this.color = CONFIG.colors[paletteIndex];
        }

        // `step` is elapsed time in 60fps-frames, so motion looks the same on
        // 60Hz, 120Hz and 144Hz screens.
        update(time, step) {
            const t = time * CONFIG.flowSpeed * this.speed;

            const driftX = Math.sin(t * 1.65 + this.phase) * CONFIG.driftX * this.wander;
            const driftY = Math.cos(t * 1.35 + this.phase2) * CONFIG.driftY * this.wander;

            const waveX = Math.sin(this.homeY * 0.010 + t * 3.1 + this.phase2) * CONFIG.flowStrength;
            const waveY = Math.cos(this.homeX * 0.008 - t * 2.7 + this.phase) * CONFIG.flowStrength * 0.62;

            let targetX = this.homeX + driftX + waveX;
            let targetY = this.homeY + driftY + waveY;

            // The cursor catches nearby particles and arranges them onto spiral
            // arms that revolve around it. Distance is measured from the HOME
            // spot, so when the cursor moves on, particles let go and fly back.
            const idle = CONFIG.spiralIdleMs > 0 && (time - mouse.lastMove) > CONFIG.spiralIdleMs;
            if (mouse.active && !idle && !reducedMotion) {
                const dx = this.homeX - mouse.x;
                const dy = this.homeY - mouse.y;
                const d = Math.sqrt(dx * dx + dy * dy);
                if (!this.captured && d < CONFIG.mouseRadius) this.captured = true;
                else if (this.captured && d > CONFIG.mouseRadius * CONFIG.mouseRelease) this.captured = false;
            } else {
                this.captured = false;
            }

            const grabEase = 1 - Math.pow(1 - CONFIG.spiralGrabSpeed, step);
            this.grab += ((this.captured ? 1 : 0) - this.grab) * grabEase;

            if (this.grab > 0.001) {
                const r = CONFIG.spiralCore + (CONFIG.spiralRadius - CONFIG.spiralCore) * this.armT;
                const armBase = (this.arm / CONFIG.spiralArms) * Math.PI * 2;
                const spin = time * CONFIG.spiralSpin;
                const ang = armBase + CONFIG.spiralDir * (spin - r * CONFIG.spiralTwist) + this.armJitter;

                const spiralX = mouse.x + Math.cos(ang) * r;
                const spiralY = mouse.y + Math.sin(ang) * r;

                const g = this.grab * this.grab * (3 - 2 * this.grab);
                targetX += (spiralX - targetX) * g;
                targetY += (spiralY - targetY) * g;
            }

            const k = CONFIG.springStrength * (1 + this.grab * CONFIG.spiralSnap) * step;
            const damping = Math.pow(CONFIG.friction, step);
            this.vx += (targetX - this.x) * k;
            this.vy += (targetY - this.y) * k;
            this.vx *= damping;
            this.vy *= damping;
            this.x += this.vx * step;
            this.y += this.vy * step;

            // Point the dash along its direction of travel.
            const speed2 = this.vx * this.vx + this.vy * this.vy;
            if (speed2 > 0.003) {
                const desired = Math.atan2(this.vy, this.vx);
                let delta = desired - this.angle;
                while (delta > Math.PI) delta -= Math.PI * 2;
                while (delta < -Math.PI) delta += Math.PI * 2;
                this.angle += delta * (1 - Math.pow(1 - 0.11, step));
            }
        }

        draw(time) {
            const shimmer = 0.88 + Math.sin(time * 0.0012 + this.phase) * 0.12;
            const c = Math.cos(this.angle);
            const s = Math.sin(this.angle);
            const half = this.length * 0.5;

            ctx.setTransform(dpr * c, dpr * s, -dpr * s, dpr * c, dpr * this.x, dpr * this.y);
            ctx.globalAlpha = clamp(this.alpha * shimmer, 0, 1);
            ctx.strokeStyle = this.color;
            ctx.beginPath();
            ctx.moveTo(-half, 0);
            ctx.lineTo(half, 0);
            ctx.stroke();
        }
    }

    function createParticles() {
        const count = width < 760 ? CONFIG.mobileParticles : CONFIG.desktopParticles;
        particles = Array.from({ length: count }, (_, index) => new Particle(index, count));
    }

    // Dust never moves, so paint it once onto its own layer and just stamp
    // that layer every frame.
    function createDust() {
        dustLayer = parentDoc.createElement("canvas");
        dustLayer.width = canvas.width;
        dustLayer.height = canvas.height;
        const dctx = dustLayer.getContext("2d");
        dctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        dctx.fillStyle = CONFIG.dustColor;

        const count = Math.round(width * height * CONFIG.dustDensity);
        for (let i = 0; i < count; i++) {
            dctx.globalAlpha = rand(CONFIG.dustMinAlpha, CONFIG.dustMaxAlpha);
            dctx.beginPath();
            dctx.arc(Math.random() * width, Math.random() * height,
                     rand(CONFIG.dustMinR, CONFIG.dustMaxR), 0, Math.PI * 2);
            dctx.fill();
        }
    }

    function onMouseMove(event) {
        mouse.x = event.clientX;
        mouse.y = event.clientY;
        mouse.active = true;
        mouse.lastMove = parentWin.performance.now();
    }
    function onMouseLeave() { mouse.active = false; }
    function onTouchMove(event) {
        if (!event.touches?.length) return;
        mouse.x = event.touches[0].clientX;
        mouse.y = event.touches[0].clientY;
        mouse.active = true;
        mouse.lastMove = parentWin.performance.now();
    }
    function onTouchEnd() { mouse.active = false; }

    function onResize() {
        resizeCanvas();
        createParticles();
        createDust();
    }

    function animate(time) {
        if (destroyed) return;

        if (lastTime === null) lastTime = time;
        const step = clamp((time - lastTime) / 16.667, 0.25, 3);
        lastTime = time;

        if ((frame++ & 15) === 0) recenter();

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalAlpha = 1;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(dustLayer, 0, 0);

        ctx.lineWidth = CONFIG.lineWidth;
        ctx.lineCap = "round";
        for (const particle of particles) {
            particle.update(time, step);
            particle.draw(time);
        }

        rafId = parentWin.requestAnimationFrame(animate);
    }

    parentDoc.addEventListener("mousemove", onMouseMove, { passive: true });
    parentDoc.documentElement.addEventListener("mouseleave", onMouseLeave, { passive: true });
    parentWin.addEventListener("blur", onMouseLeave, { passive: true });
    parentDoc.addEventListener("touchmove", onTouchMove, { passive: true });
    parentDoc.addEventListener("touchend", onTouchEnd, { passive: true });
    parentWin.addEventListener("resize", onResize, { passive: true });

    resizeCanvas();
    createParticles();
    createDust();
    rafId = parentWin.requestAnimationFrame(animate);

    parentWin.__antigravityParticleField = {
        version: VERSION,
        destroy() {
            destroyed = true;
            if (rafId !== null) parentWin.cancelAnimationFrame(rafId);
            parentDoc.removeEventListener("mousemove", onMouseMove);
            parentDoc.documentElement.removeEventListener("mouseleave", onMouseLeave);
            parentWin.removeEventListener("blur", onMouseLeave);
            parentDoc.removeEventListener("touchmove", onTouchMove);
            parentDoc.removeEventListener("touchend", onTouchEnd);
            parentWin.removeEventListener("resize", onResize);
            canvas.remove();
            style.remove();
        }
    };
})();
</script>
"""


def inject_particle_background():
    """Add the Antigravity-style particle field behind the whole app.

    Safe to call on every rerun and from several places: if the same version
    of the effect is already running in the browser it does nothing, so the
    particles never restart or flicker.
    """
    version = hashlib.md5((_SCRIPT + PAGE_BACKGROUND).encode("utf-8")).hexdigest()[:10]
    script = _SCRIPT.replace("__VERSION__", version).replace("__PAGE_BG__", PAGE_BACKGROUND)
    components.html(script, height=0, width=0)