import streamlit.components.v1 as components


def inject_particle_background():
    components.html(
        """
        <script>
        (() => {
            const parentDoc = window.parent.document;
            const parentWin = window.parent;

            // Prevent duplicates when Streamlit reruns
            if (parentWin.__antigravityBgInit) {
                return;
            }
            parentWin.__antigravityBgInit = true;

            // ------------------------------------------------------------
            // CREATE CANVAS
            // ------------------------------------------------------------

            const canvas = parentDoc.createElement("canvas");
            canvas.id = "antigravity-particle-canvas";

            canvas.style.position = "fixed";
            canvas.style.top = "0";
            canvas.style.left = "0";
            canvas.style.width = "100vw";
            canvas.style.height = "100vh";
            canvas.style.pointerEvents = "none";
            canvas.style.zIndex = "-1";
            canvas.style.opacity = "0.5";

            parentDoc.body.insertBefore(canvas, parentDoc.body.firstChild);

            const ctx = canvas.getContext("2d");

            // ------------------------------------------------------------
            // CONFIG
            // ------------------------------------------------------------

            const CONFIG = {
                particleCount: 80,

                // Particle appearance
                minLength: 1,
                maxLength: 2.2,
                lineWidth: 1,

                // Cursor interaction
                mouseRadius: 130,
                mouseForce: 0.35,

                // Movement
                springStrength: 0.025,
                friction: 0.93,

                // Very subtle floating motion
                driftStrength: 0.006,

                // Colors inspired by the reference
                colors: [
                    "#4263EB",
                    "#5F3DC4",
                    "#7048E8",
                    "#9C36B5",
                    "#C2255C",
                    "#E64980"
                ]
            };

            let width;
            let height;
            let dpr;

            let particles = [];

            const mouse = {
                x: -9999,
                y: -9999,
                active: false
            };

            // ------------------------------------------------------------
            // RESIZE
            // ------------------------------------------------------------

            function resizeCanvas() {
                dpr = Math.min(parentWin.devicePixelRatio || 1, 2);

                width = parentWin.innerWidth;
                height = parentWin.innerHeight;

                canvas.width = width * dpr;
                canvas.height = height * dpr;

                canvas.style.width = width + "px";
                canvas.style.height = height + "px";

                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            }

            resizeCanvas();

            // ------------------------------------------------------------
            // PARTICLE
            // ------------------------------------------------------------

            class Particle {
                constructor() {
                    this.originX = Math.random() * width;
                    this.originY = Math.random() * height;

                    this.x = this.originX;
                    this.y = this.originY;

                    this.vx = 0;
                    this.vy = 0;

                    this.length =
                        CONFIG.minLength +
                        Math.random() *
                            (CONFIG.maxLength - CONFIG.minLength);

                    this.angle = Math.random() * Math.PI * 2;

                    this.color =
                        CONFIG.colors[
                            Math.floor(
                                Math.random() * CONFIG.colors.length
                            )
                        ];

                    this.alpha = 0.12 + Math.random() * 0.25;

                    this.phase = Math.random() * Math.PI * 2;
                }

                update(time) {

                    // ----------------------------------------------------
                    // Cursor repulsion
                    // ----------------------------------------------------

                    if (mouse.active) {
                        const dx = this.x - mouse.x;
                        const dy = this.y - mouse.y;

                        const distanceSquared = dx * dx + dy * dy;

                        if (
                            distanceSquared <
                                CONFIG.mouseRadius * CONFIG.mouseRadius &&
                            distanceSquared > 0
                        ) {
                            const distance = Math.sqrt(distanceSquared);

                            const force =
                                (CONFIG.mouseRadius - distance) /
                                CONFIG.mouseRadius;

                            const directionX = dx / distance;
                            const directionY = dy / distance;

                            const strength =
                                force *
                                force *
                                CONFIG.mouseForce;

                            this.vx += directionX * strength;
                            this.vy += directionY * strength;
                        }
                    }

                    // ----------------------------------------------------
                    // Spring back to original position
                    // ----------------------------------------------------

                    const springX = this.originX - this.x;
                    const springY = this.originY - this.y;

                    this.vx += springX * CONFIG.springStrength;
                    this.vy += springY * CONFIG.springStrength;

                    // ----------------------------------------------------
                    // Tiny ambient movement
                    // ----------------------------------------------------

                    this.vx +=
                        Math.sin(time * 0.0004 + this.phase) *
                        CONFIG.driftStrength;

                    this.vy +=
                        Math.cos(time * 0.00035 + this.phase) *
                        CONFIG.driftStrength;

                    // ----------------------------------------------------
                    // Friction
                    // ----------------------------------------------------

                    this.vx *= CONFIG.friction;
                    this.vy *= CONFIG.friction;

                    this.x += this.vx;
                    this.y += this.vy;

                    // Point little dash in movement direction
                    if (
                        Math.abs(this.vx) > 0.02 ||
                        Math.abs(this.vy) > 0.02
                    ) {
                        this.angle = Math.atan2(this.vy, this.vx);
                    }
                }

                draw() {
                    ctx.save();

                    ctx.translate(this.x, this.y);
                    ctx.rotate(this.angle);

                    ctx.beginPath();

                    ctx.moveTo(-this.length / 2, 0);
                    ctx.lineTo(this.length / 2, 0);

                    ctx.strokeStyle = this.color;
                    ctx.globalAlpha = this.alpha;

                    ctx.lineWidth = CONFIG.lineWidth;
                    ctx.lineCap = "round";

                    ctx.stroke();

                    ctx.restore();
                }
            }

            // ------------------------------------------------------------
            // CREATE PARTICLES
            // ------------------------------------------------------------

            function createParticles() {
                particles = [];

                for (let i = 0; i < CONFIG.particleCount; i++) {
                    particles.push(new Particle());
                }
            }

            createParticles();

            // ------------------------------------------------------------
            // MOUSE
            // ------------------------------------------------------------

            parentDoc.addEventListener(
                "mousemove",
                (event) => {
                    mouse.x = event.clientX;
                    mouse.y = event.clientY;
                    mouse.active = true;
                },
                { passive: true }
            );

            parentDoc.addEventListener(
                "mouseleave",
                () => {
                    mouse.active = false;
                },
                { passive: true }
            );

            // Touch support
            parentDoc.addEventListener(
                "touchmove",
                (event) => {
                    if (!event.touches.length) return;

                    mouse.x = event.touches[0].clientX;
                    mouse.y = event.touches[0].clientY;
                    mouse.active = true;
                },
                { passive: true }
            );

            parentDoc.addEventListener(
                "touchend",
                () => {
                    mouse.active = false;
                },
                { passive: true }
            );

            // ------------------------------------------------------------
            // RESIZE
            // ------------------------------------------------------------

            parentWin.addEventListener("resize", () => {
                resizeCanvas();

                // Redistribute particles for new screen dimensions
                createParticles();
            });

            // ------------------------------------------------------------
            // ANIMATION
            // ------------------------------------------------------------

            function animate(time) {
                ctx.clearRect(0, 0, width, height);

                for (const particle of particles) {
                    particle.update(time);
                    particle.draw();
                }

                parentWin.requestAnimationFrame(animate);
            }

            parentWin.requestAnimationFrame(animate);

        })();
        </script>
        """,
        height=0,
        width=0,
    )