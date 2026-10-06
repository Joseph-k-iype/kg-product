import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";

const vertexSource = `
attribute vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }
`;

const fragmentSource = `
precision mediump float;
uniform vec2 resolution;
uniform vec2 pointer;
uniform float time;
uniform float pixelRatio;
void main() {
  float spacing = 3.8 * pixelRatio;
  vec2 cell = (floor(gl_FragCoord.xy / spacing) + 0.5) * spacing;
  vec2 uv = cell / resolution;
  vec2 p = (uv - 0.5) * vec2(resolution.x / resolution.y * 0.72, 0.85);
  p += (pointer - 0.5) * 0.055;
  float t = time * 0.20;
  vec2 a = p - vec2(0.08 + sin(t) * 0.09, 0.10 + cos(t * 0.8) * 0.04);
  vec2 b = p - vec2(-0.22 + cos(t * 0.7) * 0.05, -0.16);
  vec2 c = p - vec2(0.27, -0.14 + sin(t * 0.6) * 0.06);
  float field = exp(-dot(a, a) * 10.0)
              + 0.68 * exp(-dot(b, b) * 18.0)
              + 0.62 * exp(-dot(c, c) * 21.0);
  float folds = sin(p.x * 17.0 + sin(p.y * 11.0 + t) * 1.7 - t) * 0.12;
  float density = smoothstep(0.08, 1.25, field + folds * field);
  float radius = 0.04 + density * 0.40;
  float dotMask = 1.0 - smoothstep(radius - 0.065, radius + 0.065,
                                  length(fract(gl_FragCoord.xy / spacing) - 0.5));
  float edge = smoothstep(0.0, 0.14, uv.x) * smoothstep(0.0, 0.14, 1.0 - uv.x)
             * smoothstep(0.0, 0.13, uv.y) * smoothstep(0.0, 0.13, 1.0 - uv.y);
  vec3 red = mix(vec3(0.89, 0.11, 0.07), vec3(0.71, 0.04, 0.025), density * 0.48);
  gl_FragColor = vec4(red, dotMask * density * edge);
}
`;

/** Decorative artwork is isolated from product state and never blocks a workflow. */
export function KnowledgeSignal() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeRef = useRef(0);
  const [paused, setPaused] = useState(false);
  const [available, setAvailable] = useState(false);
  const [reduced, setReduced] = useState(false);
  const [contextVersion, setContextVersion] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(media.matches);
    let gl: WebGLRenderingContext | null = null;
    try {
      gl = canvas.getContext("webgl", {
        alpha: true,
        premultipliedAlpha: false,
        antialias: false,
        depth: false,
      });
    } catch {
      /* Browsers may deny GPU access; the static artwork remains. */
    }
    if (!gl) return;
    const context = gl;
    const shaders: WebGLShader[] = [];
    let program: WebGLProgram | null = null;
    let buffer: WebGLBuffer | null = null;
    function compile(type: number, source: string) {
      const shader = context.createShader(type);
      if (!shader) throw new Error("Shader allocation failed");
      shaders.push(shader);
      context.shaderSource(shader, source);
      context.compileShader(shader);
      if (!context.getShaderParameter(shader, context.COMPILE_STATUS))
        throw new Error("Shader unavailable");
      return shader;
    }
    try {
      const vertex = compile(context.VERTEX_SHADER, vertexSource);
      const fragment = compile(context.FRAGMENT_SHADER, fragmentSource);
      program = context.createProgram();
      if (!program) throw new Error("Shader program unavailable");
      context.attachShader(program, vertex);
      context.attachShader(program, fragment);
      context.linkProgram(program);
      if (!context.getProgramParameter(program, context.LINK_STATUS))
        throw new Error("Shader link failed");
      buffer = context.createBuffer();
      if (!buffer) throw new Error("Shader buffer unavailable");
      context.useProgram(program);
      context.bindBuffer(context.ARRAY_BUFFER, buffer);
      context.bufferData(
        context.ARRAY_BUFFER,
        new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
        context.STATIC_DRAW,
      );
      const position = context.getAttribLocation(program, "position");
      context.enableVertexAttribArray(position);
      context.vertexAttribPointer(position, 2, context.FLOAT, false, 0, 0);
    } catch {
      shaders.forEach((shader) => context.deleteShader(shader));
      if (buffer) context.deleteBuffer(buffer);
      if (program) context.deleteProgram(program);
      setAvailable(false);
      return;
    }
    const resolution = context.getUniformLocation(program, "resolution");
    const clock = context.getUniformLocation(program, "time");
    const pointer = context.getUniformLocation(program, "pointer");
    const ratio = context.getUniformLocation(program, "pixelRatio");
    let frame = 0,
      elapsed = timeRef.current,
      last = 0,
      visible = true,
      lost = false;
    let point: [number, number] = [0.5, 0.5];
    const canAnimate = () =>
      !paused && !media.matches && visible && !document.hidden && !lost;
    function draw() {
      if (lost) return;
      const dpr = Math.min(devicePixelRatio || 1, 1.5);
      const width = Math.max(1, Math.round(container!.clientWidth * dpr));
      const height = Math.max(1, Math.round(container!.clientHeight * dpr));
      if (canvas!.width !== width || canvas!.height !== height) {
        canvas!.width = width;
        canvas!.height = height;
      }
      context.viewport(0, 0, width, height);
      context.uniform2f(resolution, width, height);
      context.uniform1f(ratio, dpr);
      context.uniform1f(clock, elapsed);
      context.uniform2f(pointer, point[0], point[1]);
      context.drawArrays(context.TRIANGLES, 0, 6);
    }
    function tick(now: number) {
      frame = 0;
      if (!canAnimate()) return;
      // Limit to ~30fps. Hidden/offscreen artwork requests no frames.
      if (!last || now - last >= 32) {
        elapsed += last ? Math.min((now - last) / 1000, 0.1) : 0;
        timeRef.current = elapsed;
        last = now;
        draw();
      }
      frame = requestAnimationFrame(tick);
    }
    function sync() {
      cancelAnimationFrame(frame);
      frame = 0;
      last = 0;
      setReduced(media.matches);
      if (media.matches) {
        elapsed = 0;
        timeRef.current = 0;
        point = [0.5, 0.5];
      }
      draw();
      if (canAnimate()) frame = requestAnimationFrame(tick);
    }
    const onPointer = (event: PointerEvent) => {
      if (!canAnimate()) return;
      const rect = container!.getBoundingClientRect();
      point = [
        (event.clientX - rect.left) / rect.width,
        1 - (event.clientY - rect.top) / rect.height,
      ];
    };
    const onLeave = () => {
      point = [0.5, 0.5];
    };
    const onLost = (event: Event) => {
      event.preventDefault();
      lost = true;
      cancelAnimationFrame(frame);
      setAvailable(false);
    };
    const onRestored = () => setContextVersion((version) => version + 1);
    const resize = new ResizeObserver(() => draw());
    resize.observe(container);
    const intersection = new IntersectionObserver(([entry]) => {
      if (!entry) return;
      visible = entry.isIntersecting;
      sync();
    });
    intersection.observe(container);
    container.addEventListener("pointermove", onPointer);
    container.addEventListener("pointerleave", onLeave);
    canvas.addEventListener("webglcontextlost", onLost);
    canvas.addEventListener("webglcontextrestored", onRestored);
    document.addEventListener("visibilitychange", sync);
    media.addEventListener("change", sync);
    setAvailable(true);
    sync();
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      intersection.disconnect();
      container.removeEventListener("pointermove", onPointer);
      container.removeEventListener("pointerleave", onLeave);
      canvas.removeEventListener("webglcontextlost", onLost);
      canvas.removeEventListener("webglcontextrestored", onRestored);
      document.removeEventListener("visibilitychange", sync);
      media.removeEventListener("change", sync);
      shaders.forEach((shader) => context.deleteShader(shader));
      context.deleteBuffer(buffer);
      context.deleteProgram(program);
    };
  }, [paused, contextVersion]);

  return (
    <div className="hero-visual">
      <div ref={containerRef} className="knowledge-signal" aria-hidden="true">
        <img
          className="signal-fallback"
          src="/artwork/knowledge-signal.png"
          alt=""
          hidden={available}
        />
        <canvas ref={canvasRef} hidden={!available} />
      </div>
      {available && !reduced && (
        <button
          className="signal-control icon-button"
          aria-label={paused ? "Play visual" : "Pause visual"}
          onClick={() => setPaused((value) => !value)}
        >
          {paused ? <Play size={12} /> : <Pause size={12} />}
        </button>
      )}
    </div>
  );
}
