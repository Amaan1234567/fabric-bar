import gi
from enum import Enum
import OpenGL.GL as GL
from collections.abc import Iterable
from typing import cast, overload, Literal
from OpenGL.GL.shaders import compileShader, compileProgram

from fabric import Application, Signal, Property
from fabric.widgets.widget import Widget

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib


class ShadertoyUniformType(Enum):
    FLOAT = 1
    INTEGER = 2
    VECTOR = 3
    TEXTURE = 4


class ShadertoyCompileError(Exception): ...


class Shadertoy(Gtk.GLArea, Widget):
    @Signal
    def ready(self) -> None: ...

    @Property(str, "read-write")
    def shader_buffer(self) -> str:
        return self._shader_buffer

    @shader_buffer.setter
    def shader_buffer(self, shader_buffer: str) -> None:
        self._shader_buffer = shader_buffer
        if not self._ready:
            return
        self._shader_uniforms.clear()
        self.do_realize()
        self.queue_draw()
        return

    DEFAULT_VERTEX_SHADER = """
    #version 330
    in vec2 position;
    void main() {
        gl_Position = vec4(position, 0.0, 1.0);
    }
    """

    DEFAULT_FRAGMENT_UNIFORMS = """
    #version 330
    uniform vec3 iResolution;
    uniform float iTime;
    uniform float iTimeDelta;
    uniform float iFrameRate;
    uniform int iFrame;
    uniform float iChannelTime[4];
    uniform vec3 iChannelResolution[4];
    uniform vec4 iMouse;
    uniform sampler2D iChannel0;
    uniform sampler2D iChannel1;
    uniform sampler2D iChannel2;
    uniform sampler2D iChannel3;
    uniform vec4 iDate;
    uniform float iSampleRate;
    """

    FRAGMENT_MAIN_FUNCTION = """
    void main() {
        mainImage(gl_FragColor, gl_FragCoord.xy);
    }
    """

    def __init__(
        self,
        shader_buffer: str,
        shader_uniforms: (
            list[
                tuple[
                    str,
                    ShadertoyUniformType,
                    bool | float | int | tuple[float, ...] | GdkPixbuf.Pixbuf,
                ]
            ]
            | None
        ) = None,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes: Iterable[str] | str | None = None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align: (
            Literal["fill", "start", "end", "center", "baseline"] | Gtk.Align | None
        ) = None,
        v_align: (
            Literal["fill", "start", "end", "center", "baseline"] | Gtk.Align | None
        ) = None,
        h_expand: bool = False,
        v_expand: bool = False,
        size: Iterable[int] | int | None = None,
        **kwargs,
    ):
        Gtk.GLArea.__init__(self)
        Widget.__init__(
            self,
            name,
            visible,
            all_visible,
            style,
            style_classes,
            tooltip_text,
            tooltip_markup,
            h_align,
            v_align,
            h_expand,
            v_expand,
            size,
            **kwargs,
        )
        self._shader_buffer = shader_buffer
        self._shader_uniforms = shader_uniforms or []

        self.set_required_version(3, 3)
        self.set_has_depth_buffer(False)
        self.set_has_stencil_buffer(False)

        self._ready = False
        self._program = None
        self._vao = None
        self._quad_vbo = None
        self._texture_units = {}

        self._start_time = GLib.get_monotonic_time() / 1e6
        self._frame_time = self._start_time
        self._frame_count = 0

        self._tick_id = self.add_tick_callback(lambda *_: (self.queue_draw(), True)[1])

    def do_bake_program(self):
        try:
            vertex_shader = compileShader(
                self.DEFAULT_VERTEX_SHADER, GL.GL_VERTEX_SHADER
            )
            fragment_shader = compileShader(
                self.DEFAULT_FRAGMENT_UNIFORMS
                + self._shader_buffer
                + self.FRAGMENT_MAIN_FUNCTION,
                GL.GL_FRAGMENT_SHADER,
            )
        except Exception as e:
            raise ShadertoyCompileError(
                f"couldn't compile the provided shader, OpenGL error:\n {e}"
            )

        return compileProgram(vertex_shader, fragment_shader)

    def do_realize(self, *_):
        Gtk.GLArea.do_realize(self)
        if not self._ready:
            ctx = self.get_context()
            if (err := self.get_error()) or not ctx:
                raise RuntimeError(
                    f"couldn't initialize the drawing context, error: {err or 'context is None'}"
                )
            ctx.make_current()

        if self._program:
            GL.glDeleteProgram(self._program)
            self._program = None
        self._program = self.do_bake_program()

        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        self._quad_vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._quad_vbo)

        quad_verts = (-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0)
        array_type = GL.GLfloat * len(quad_verts)
        GL.glBufferData(
            GL.GL_ARRAY_BUFFER,
            len(quad_verts) * 4,
            array_type(*quad_verts),
            GL.GL_STATIC_DRAW,
        )

        self._vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self._vao)

        position = GL.glGetAttribLocation(self._program, "position")
        GL.glEnableVertexAttribArray(position)
        GL.glVertexAttribPointer(position, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        for uname, utype, uvalue in self._shader_uniforms:
            self.set_uniform(uname, utype, uvalue)  # type: ignore

        self._ready = True
        self.ready()
        return

    def do_get_timing(self) -> tuple[float, float, float]:
        current_time = GLib.get_monotonic_time() / 1e6
        delta_time = current_time - self._frame_time
        return current_time, delta_time, (1.0 / delta_time) if delta_time > 0 else 0.0

    def do_post_render(self, time: float):
        self._frame_time = time
        self._frame_count += 1
        return

    def do_render(self, ctx: Gdk.GLContext):
        if not self._program:
            if self._tick_id:
                self.remove_tick_callback(self._tick_id)
            self._tick_id = 0
            return False

        GL.glUseProgram(self._program)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        alloc = self.get_allocation()
        width: int = alloc.width
        height: int = alloc.height
        mouse_pos = cast(tuple[int, int], self.get_pointer())

        current_time, delta_time, frame_rate = self.do_get_timing()

        self.set_uniform(
            "iTime", ShadertoyUniformType.FLOAT, current_time - self._start_time
        )
        self.set_uniform("iFrame", ShadertoyUniformType.INTEGER, self._frame_count)
        self.set_uniform("iTimeDelta", ShadertoyUniformType.FLOAT, delta_time)
        self.set_uniform("iFrameRate", ShadertoyUniformType.FLOAT, frame_rate)
        self.set_uniform(
            "iResolution", ShadertoyUniformType.VECTOR, (width, height, 1.0)
        )
        self.set_uniform(
            "iMouse",
            ShadertoyUniformType.VECTOR,
            (mouse_pos[0], height - mouse_pos[1], 0, 0),
        )

        GL.glBindVertexArray(self._vao)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        self.do_post_render(current_time)
        return True

    def do_resize(self, width: int, height: int):
        Gtk.GLArea.do_resize(self, width, height)
        GL.glViewport(0, 0, width, height)
        return

    @overload
    def set_uniform(
        self, name: str, type: Literal[ShadertoyUniformType.FLOAT], value: float
    ): ...

    @overload
    def set_uniform(
        self, name: str, type: Literal[ShadertoyUniformType.INTEGER], value: int
    ): ...

    @overload
    def set_uniform(
        self,
        name: str,
        type: Literal[ShadertoyUniformType.VECTOR],
        value: tuple[float, ...],
    ): ...

    @overload
    def set_uniform(
        self,
        name: str,
        type: Literal[ShadertoyUniformType.TEXTURE],
        value: GdkPixbuf.Pixbuf,
    ): ...

    def set_uniform(
        self,
        name: str,
        type: ShadertoyUniformType,
        value: bool | float | int | tuple[float, ...] | GdkPixbuf.Pixbuf,
    ):
        if not self._program:
            raise RuntimeError("the shader program is not initialized")
        GL.glUseProgram(self._program)
        location = GL.glGetUniformLocation(self._program, name)
        match type:
            case ShadertoyUniformType.VECTOR:
                value = cast(tuple[float, ...], value)
                (
                    GL.glUniform2f
                    if (vlen := len(value)) == 2
                    else GL.glUniform3f if vlen == 3 else GL.glUniform4f
                )(location, *value)
            case ShadertoyUniformType.FLOAT:
                GL.glUniform1f(location, value)
            case ShadertoyUniformType.INTEGER:
                GL.glUniform1i(location, value)
            case ShadertoyUniformType.TEXTURE:
                value = cast(GdkPixbuf.Pixbuf, value).flip(False)
                format = GL.GL_RGBA if value.get_has_alpha() else GL.GL_RGB

                if name not in self._texture_units:
                    texture = GL.glGenTextures(1)
                    self._texture_units[name] = (len(self._texture_units), texture)
                else:
                    texture_unit, texture = self._texture_units[name]

                texture_unit = self._texture_units[name][0]
                GL.glActiveTexture(GL.GL_TEXTURE0 + texture_unit)
                GL.glBindTexture(GL.GL_TEXTURE_2D, texture)

                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
                GL.glTexParameteri(
                    GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR
                )
                GL.glTexParameteri(
                    GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR
                )

                GL.glTexImage2D(
                    GL.GL_TEXTURE_2D,
                    0,
                    format,
                    value.get_width(),
                    value.get_height(),
                    0,
                    format,
                    GL.GL_UNSIGNED_BYTE,
                    value.get_pixels(),
                )
                GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
                GL.glUniform1i(location, texture_unit)


# =======================
# GLSL shader
# =======================
LENS_SHADER = """
#define width 0.33
#define height 0.33
#define radius 0.1
#define lens_refraction 0.1
#define sharp 0.1

float _clamp(float a){
    return clamp(a,0.,1.);
}

float box( in vec2 p, in vec2 b, in vec4 r )
{
    r.xy = (p.x>0.0)?r.xy : r.zw;
    r.x  = (p.y>0.0)?r.x  : r.y;
    vec2 q = abs(p)-b+r.x;
    return min(max(q.x,q.y),0.0) + length(max(q,0.0)) - r.x;
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    fragColor = vec4(0);

    vec2 ir = iResolution.xy;
    vec2 wh = vec2(width,height)/2.0*ir.x/ir.y;
    vec4 vr = vec4(radius)/2.0*ir.x/ir.y;

    vec2 uv = fragCoord/ir;
    vec2 mouse = iMouse.xy;
    if (length(mouse)<1.0) {
        mouse = ir/2.0;
    } vec2 m2 = (uv-mouse/ir);

    float rb1 =  _clamp( -box(vec2(m2.x*ir.x/ir.y,m2.y), wh, vr)/sharp*32.0);
    float rb2 =  _clamp(-box(vec2(m2.x*ir.x/ir.y,m2.y), wh+1.0/ir.y, vr)/sharp*16.0) - _clamp(-box(vec2(m2.x*ir.x/ir.y,m2.y), wh, vr)/sharp*16.0);
    float rb3 = _clamp(-box(vec2(m2.x*ir.x/ir.y,m2.y), wh+4.0/ir.y, vr)/sharp*4.0) - _clamp(-box(vec2(m2.x*ir.x/ir.y,m2.y), wh-4.0/ir.y, vr)/sharp*4.0);

    float transition = smoothstep(0.0, 1.0, rb1);

    if (transition>0.0) {
        vec2 lens = (uv-0.5)*sin(pow(
            _clamp(-box(vec2(m2.x*ir.x/ir.y,m2.y), wh, vr)/lens_refraction),
        0.25)*1.57)+0.5;

        float total = 0.0;
        for (float x = -4.0; x <= 4.0; x++) {
            for (float y = -4.0; y <= 4.0; y++) {
                vec2 blur = vec2(x, y) * 0.5 / ir;
                fragColor += texture(iChannel0, lens+blur);
                total += 1.0;
            }
        } fragColor/=total;

        float gradient = _clamp(clamp(m2.y,0.0,0.2)+0.1)/2.0 + _clamp(clamp(-m2.y,-1.0,0.2)*rb3+0.1)/2.0;
        vec4 lighting = fragColor+1.0*vec4(rb2)+gradient*1.0;

        fragColor = mix(texture(iChannel0, uv), lighting, transition);

    } else {
        fragColor = texture(iChannel0, uv);
    }
}
"""


# =======================
# Run the GTK app
# =======================
def make_window_transparent(win):
    screen = win.get_screen()
    visual = screen.get_rgba_visual()
    if visual is not None and screen.is_composited():
        win.set_visual(visual)
    win.set_app_paintable(True)


if __name__ == "__main__":
    tex = GdkPixbuf.Pixbuf.new_from_file("/home/amaan/Pictures/backgrounds/Lofi-Urban-Nightscape.png")

    shader_bg = Shadertoy(
        shader_buffer=LENS_SHADER,
        shader_uniforms=[("iChannel0", ShadertoyUniformType.TEXTURE, tex)],
        h_expand=True,
        v_expand=True,
    )

    overlay = Gtk.Overlay()
    overlay.add(shader_bg)  # Shader at bottom

    # Foreground content
    lbl = Gtk.Label(label="Transparent window with shader background")
    overlay.add_overlay(lbl)

    # Window setup
    win = Gtk.Window()
    win.connect("destroy", Gtk.main_quit)
    make_window_transparent(win)  # Enable transparency
    win.add(overlay)
    win.set_default_size(800, 600)
    win.show_all()

    Gtk.main()