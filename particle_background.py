import streamlit.components.v1 as components


def inject_particle_background():
    """Inject an Antigravity-style interactive particle field behind a Streamlit UI."""

    components.html(
        r"""
        <script>
        (() => {
            const parentDoc = window.parent.document;
            const parentWin = window.parent;

            // Streamlit reruns the component iframe. Tear down the previous
            // animation so code/config changes take effect without a hard refresh.
            if (parentWin.__antigravityParticleField?.destroy) {
                parentWin.__antigravityParticleField.destroy();
            }

            const oldCanvas = parentDoc.getElementById("antigravity-particle-canvas");
            if (oldCanvas) oldCanvas.remove();

            const oldStyle = parentDoc.getElementById("antigravity-particle-style");
            if (oldStyle) oldStyle.remove();

            // Keep the Streamlit UI above the canvas while allowing the canvas
            // to show through the app background.
            const style = parentDoc.createElement("style");
            style.id = "antigravity-particle-style";
            style.textContent = `
                html, body {
                    background: #000000 !important;
                }

                [data-testid="stAppViewContainer"],
                .stApp {
                    background: transparent !important;
                }

                [data-testid="stAppViewContainer"] > section,
                [data-testid="stHeader"],
                [data-testid="stToolbar"] {
                    position: relative;
                    z-index: 2;
                }

                #antigravity-particle-canvas {
                    position: fixed;
                    inset: 0;
                    width: 100vw;
                    height: 100vh;
                    pointer-events: none;
                    z-index: 0;
                }
            `;
            parentDoc.head.appendChild(style);

            const canvas = parentDoc.createElement("canvas");
            canvas.id = "antigravity-particle-canvas";
            canvas.setAttribute("aria-hidden", "true");
            parentDoc.body.insertBefore(canvas, parentDoc.body.firstChild);

            const ctx = canvas.getContext("2d", { alpha: true });

            const CONFIG = {
                // The reference is intentionally dense. Mobile uses fewer particles.
                desktopParticles: 540,
                mobileParticles: 280,

                // Elliptical field geometry. The middle stays mostly empty so hero
                // text/buttons remain readable, just like the reference.
                innerRadius: 0.30,
                outerRadius: 1.03,
                ringParticleShare: 0.88,
                radiusXViewport: 0.53,
                radiusYViewport: 0.58,
                maxRadiusX: 760,
                maxRadiusY: 470,
                centerYRatio: 0.50,

                // Particle appearance.
                minLength: 1.1,
                maxLength: 3.0,
                minAlpha: 0.16,
                maxAlpha: 0.62,
                lineWidth: 1.05,

                // Ambient flow.
                driftX: 13,
                driftY: 9,
                flowStrength: 12,
                flowSpeed: 0.00022,

                // Cursor interaction.
                mouseRadius: 175,
                mousePush: 92,

                // Spring physics.
                springStrength: 0.040,
                friction: 0.865,

                // Muted Google-Antigravity-ish palette.
                colors: [
                    "#356AE6",
                    "#536DFE",
                    "#6657D9",
                    "#7B61D1",
                    "#B149A5",
                    "#D84C78",
                    "#E26A59",
                    "#E7A23A"
                ]
            };

            let width = 0;
            let height = 0;
            let dpr = 1;
            let centerX = 0;
            let centerY = 0;
            let radiusX = 0;
            let radiusY = 0;
            let particles = [];
            let rafId = null;
            let destroyed = false;

            const mouse = {
                x: -10000,
                y: -10000,
                active: false
            };

            const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
            const rand = (a, b) => a + Math.random() * (b - a);

            function resizeCanvas() {
                dpr = Math.min(parentWin.devicePixelRatio || 1, 2);
                width = parentWin.innerWidth;
                height = parentWin.innerHeight;

                canvas.width = Math.round(width * dpr);
                canvas.height = Math.round(height * dpr);
                canvas.style.width = `${width}px`;
                canvas.style.height = `${height}px`;
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

                centerX = width * 0.50;
                centerY = height * CONFIG.centerYRatio;
                radiusX = Math.min(width * CONFIG.radiusXViewport, CONFIG.maxRadiusX);
                radiusY = Math.min(height * CONFIG.radiusYViewport, CONFIG.maxRadiusY);
            }

            function randomRingAnchor() {
                const theta = Math.random() * Math.PI * 2;

                // Uniform-ish area sampling in an annulus, with a slight bias
                // toward the middle band to recreate the reference density.
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
                // A small number of particles live outside the main ring so the
                // field softly reaches the page edges instead of ending abruptly.
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

                    // Spread palette colors through the field, then perturb the
                    // index so neighboring particles don't look striped.
                    const paletteOffset = Math.floor(Math.random() * CONFIG.colors.length);
                    const paletteIndex = (Math.floor((index / Math.max(count, 1)) * CONFIG.colors.length * 2)
                        + paletteOffset) % CONFIG.colors.length;
                    this.color = CONFIG.colors[paletteIndex];
                }

                update(time) {
                    const t = time * CONFIG.flowSpeed * this.speed;

                    // Soft procedural motion around each home point.
                    const driftX = Math.sin(t * 1.65 + this.phase) * CONFIG.driftX * this.wander;
                    const driftY = Math.cos(t * 1.35 + this.phase2) * CONFIG.driftY * this.wander;

                    // Curving vector field. This prevents the particles from merely
                    // bobbing in place and creates the flowing texture in the video.
                    const waveX = Math.sin(this.homeY * 0.010 + t * 3.1 + this.phase2) * CONFIG.flowStrength;
                    const waveY = Math.cos(this.homeX * 0.008 - t * 2.7 + this.phase) * CONFIG.flowStrength * 0.62;

                    let targetX = this.homeX + driftX + waveX;
                    let targetY = this.homeY + driftY + waveY;

                    // Cursor creates a smooth local "anti-gravity" pocket.
                    if (mouse.active) {
                        const dx = targetX - mouse.x;
                        const dy = targetY - mouse.y;
                        const d2 = dx * dx + dy * dy;
                        const r2 = CONFIG.mouseRadius * CONFIG.mouseRadius;

                        if (d2 > 0.001 && d2 < r2) {
                            const d = Math.sqrt(d2);
                            const influence = 1 - d / CONFIG.mouseRadius;
                            const eased = influence * influence * (3 - 2 * influence);
                            const push = CONFIG.mousePush * eased;
                            targetX += (dx / d) * push;
                            targetY += (dy / d) * push;
                        }
                    }

                    this.vx += (targetX - this.x) * CONFIG.springStrength;
                    this.vy += (targetY - this.y) * CONFIG.springStrength;
                    this.vx *= CONFIG.friction;
                    this.vy *= CONFIG.friction;
                    this.x += this.vx;
                    this.y += this.vy;

                    // Point the dash into the local flow direction.
                    const speed2 = this.vx * this.vx + this.vy * this.vy;
                    if (speed2 > 0.003) {
                        const desired = Math.atan2(this.vy, this.vx);
                        let delta = desired - this.angle;
                        while (delta > Math.PI) delta -= Math.PI * 2;
                        while (delta < -Math.PI) delta += Math.PI * 2;
                        this.angle += delta * 0.11;
                    }
                }

                draw(time) {
                    // Tiny breathing in opacity makes the static areas feel alive.
                    const shimmer = 0.88 + Math.sin(time * 0.0012 + this.phase) * 0.12;

                    ctx.save();
                    ctx.translate(this.x, this.y);
                    ctx.rotate(this.angle);
                    ctx.beginPath();
                    ctx.moveTo(-this.length * 0.5, 0);
                    ctx.lineTo(this.length * 0.5, 0);
                    ctx.strokeStyle = this.color;
                    ctx.globalAlpha = clamp(this.alpha * shimmer, 0, 1);
                    ctx.lineWidth = CONFIG.lineWidth;
                    ctx.lineCap = "round";
                    ctx.stroke();
                    ctx.restore();
                }
            }

            function createParticles() {
                const count = width < 760
                    ? CONFIG.mobileParticles
                    : CONFIG.desktopParticles;

                particles = Array.from({ length: count }, (_, index) => new Particle(index, count));
            }

            function onMouseMove(event) {
                mouse.x = event.clientX;
                mouse.y = event.clientY;
                mouse.active = true;
            }

            function onMouseLeave() {
                mouse.active = false;
            }

            function onTouchMove(event) {
                if (!event.touches?.length) return;
                mouse.x = event.touches[0].clientX;
                mouse.y = event.touches[0].clientY;
                mouse.active = true;
            }

            function onTouchEnd() {
                mouse.active = false;
            }

            function onResize() {
                resizeCanvas();
                createParticles();
            }

            function animate(time) {
                if (destroyed) return;
                ctx.clearRect(0, 0, width, height);

                for (const particle of particles) {
                    particle.update(time);
                    particle.draw(time);
                }

                rafId = parentWin.requestAnimationFrame(animate);
            }

            parentDoc.addEventListener("mousemove", onMouseMove, { passive: true });
            parentDoc.addEventListener("mouseleave", onMouseLeave, { passive: true });
            parentDoc.addEventListener("touchmove", onTouchMove, { passive: true });
            parentDoc.addEventListener("touchend", onTouchEnd, { passive: true });
            parentWin.addEventListener("resize", onResize, { passive: true });

            resizeCanvas();
            createParticles();
            rafId = parentWin.requestAnimationFrame(animate);

            parentWin.__antigravityParticleField = {
                destroy() {
                    destroyed = true;
                    if (rafId !== null) parentWin.cancelAnimationFrame(rafId);
                    parentDoc.removeEventListener("mousemove", onMouseMove);
                    parentDoc.removeEventListener("mouseleave", onMouseLeave);
                    parentDoc.removeEventListener("touchmove", onTouchMove);
                    parentDoc.removeEventListener("touchend", onTouchEnd);
                    parentWin.removeEventListener("resize", onResize);
                    canvas.remove();
                    style.remove();
                }
            };
        })();
        </script>
        """,
        height=0,
        width=0,
    )
