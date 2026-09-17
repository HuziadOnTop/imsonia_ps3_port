# Insomnia - PS3 Port

**Port no oficial de la novela visual "Insomnia" de Mcryx Studios a PlayStation 3.**

---

## Acerca del juego

**Insomnia** es una novela visual de terror/suspenso creada por **Mcryx Studios** usando Ren'Py. Esta es la version 1.1 (Capitulo 1 - DEMO) portada a PS3 con bugs corregidos para la plataforma.

El juego corre sobre **LuaPlayer PS3** por [3141card](https://github.com/3141card), usando el framework [DDLC-LOVE](https://github.com/LukeZGD/DDLC-LOVE) por LukeZGD, un interprete Lua con soporte grafico y de audio para el hardware de PS3.

## Compatibilidad

| Plataforma | Estado | Notas |
|---|---|---|
| **PS3 real (CFW/HEN)** | **Funciona** | Probado y verificado |
| RPCS3 (emulador) | No funciona | De momento no es compatible |

> **Importante:** Este port fue probado exclusivamente en una PlayStation 3 real con Custom Firmware. En el emulador RPCS3 no funciona de momento.

## Instalacion

### Requisitos
- PS3 con CFW (Custom Firmware) o HEN
- USB formateado en FAT32

### Pasos
1. Descarga el archivo `Insomnia-PS3-v2.pkg` desde [Releases](../../releases)
2. Copia el `.pkg` a la raiz de un USB
3. Conecta el USB a la PS3
4. Ve a **Game > Package Manager > Install Package Files**
5. Selecciona `Insomnia-PS3-v2.pkg` y espera a que se instale
6. El juego aparecera en el XMB con su icono y musica

## Controles

| Boton PS3 | Accion |
|---|---|
| **X** | Confirmar / Avanzar dialogo |
| **O** | Cancelar / Volver |
| **L1** | Activar/desactivar modo Skip (avance rapido) |
| **R1** | Activar/desactivar modo Auto (avance automatico) |
| **D-Pad** | Navegar menus |
| **Start** | Abrir menu de pausa |
| **L3 + R3** | Salir del juego |

## Sistema de guardado

El juego cuenta con sistema de guardado y carga con **3 slots** disponibles. Desde el menu de pausa (Start) podes acceder a:
- **Guardar** — Guarda tu progreso en uno de los 3 slots
- **Cargar** — Carga una partida guardada
- **Menu Principal** — Volver al inicio

Los datos de guardado se almacenan en la carpeta `savedata/` dentro del directorio del juego en la PS3.

## Estructura del proyecto

```
content/
  ICON0.PNG          # Icono del juego (XMB)
  PIC1.PNG           # Fondo del XMB
  SND0.AT3           # Musica del XMB (intro del juego, ATRAC3)
  PARAM.SFO          # Metadata del juego (TITLE_ID: DOKI12300)
  PS3LOGO.DAT        # Logo PS3
  USRDIR/
    EBOOT.BIN        # LuaPlayer PS3 (ejecutable)
    app.lua           # Punto de entrada (carga script.lua)
    insomnia-ps3/
      script.lua      # Inicializacion del engine
      game/
        engine.lua     # Motor del juego (720x480)
        script_data.lua # Guion traducido de Ren'Py a Lua
        audio/         # Efectos de sonido y musica (MP3)
        images/        # Fondos, personajes, CGs, GUI
        fonts/         # Fuentes tipograficas
      LOVE-WrapLua/    # Capa de compatibilidad LOVE -> PS3 APIs
      savedata/        # Datos de guardado
```

## Detalles tecnicos del port

### Conversion de Ren'Py a Lua
El juego original esta escrito en Ren'Py (Python). Todo el script fue traducido a tablas de comandos Lua compatibles con el engine DDLC-LOVE:
- Los comandos de Ren'Py (`scene`, `show`, `play music`, `menu`, etc.) fueron mapeados a un sistema de comandos Lua
- Las variables y flags del juego se manejan con tablas Lua
- El sistema de guardado fue adaptado para el filesystem de PS3

### Resolucion
- **720x480** (resolucion nativa de PS3 para contenido SD)

### Audio
- Efectos de sonido y musica en formato MP3
- Musica del XMB (SND0.AT3) convertida a ATRAC3 con [atracdenc](https://github.com/dcherednik/atracdenc)
- Usa un unico canal de audio (channel 1) via `snd.SetVoice` / `snd.StopVoice`

### Advertencia critica para desarrolladores
> **NUNCA** llamar a `snd.FreeVoice` en LuaPlayer PS3. Esta funcion destruye el canal de audio internamente y cualquier llamada posterior a `snd.SetVoice` en ese canal causa un segfault a nivel C que `pcall` no puede atrapar. Usar siempre `snd.StopVoice` + `snd.SetVoice` para cambiar audio.

### Formato PKG
El PKG fue generado con un builder personalizado en Python (`build_pkg_ps3.py`) que replica el formato de los PKGs homebrew funcionales:
- Content Type: `0x05` (Game Exec)
- Package Type: `0x4E`
- DRM Type: `3` (Free)
- 8 entradas de metadata
- Cifrado SHA1 stream cipher

### EBOOT
Se utiliza el EBOOT.BIN de LuaPlayer PS3 por [3141card](https://github.com/3141card), con soporte SDL, tiny3d y spu_sound. Este EBOOT tiene hardcodeado el TITLE_ID `DOKI12300`, por lo que el juego debe usar ese mismo TITLE_ID.

## Herramientas utilizadas

| Herramienta | Uso |
|---|---|
| [DDLC-LOVE](https://github.com/LukeZGD/DDLC-LOVE) | Framework base del port |
| [LuaPlayer PS3](https://github.com/3141card) | EBOOT.BIN + capa LOVE-WrapLua |
| [atracdenc](https://github.com/dcherednik/atracdenc) | Conversion de audio a ATRAC3 (SND0.AT3) |
| [FFmpeg](https://ffmpeg.org/) | Procesamiento de audio (recorte, conversion a WAV) |
| `build_pkg_ps3.py` | Generador de PKG personalizado (incluido en el repo) |

## Como construir el PKG

Si quieres reconstruir el PKG desde los archivos fuente:

```bash
python build_pkg_ps3.py
```

El script lee la carpeta `content/`, empaqueta todos los archivos con el cifrado correcto y genera `Insomnia-PS3-v2.pkg`.

**Requisitos:** Python 3.6+ (sin dependencias externas).

## Creditos

- **Insomnia** (juego original) — **Mcryx Studios** ([itch.io](https://mcryxstudios.itch.io/insomnia-jeff-the-killer))
- **DDLC-LOVE** (framework) — **LukeZGD** ([GitHub](https://github.com/LukeZGD/DDLC-LOVE))
- **LuaPlayer PS3** (EBOOT.BIN) — **3141card** ([GitHub](https://github.com/3141card))
- **atracdenc** (encoder ATRAC3) — **dcherednik** ([GitHub](https://github.com/dcherednik/atracdenc))
- **Port a PS3** — **Huziad**

## Licencia

El codigo del port (engine.lua, script.lua, script_data.lua, build_pkg_ps3.py) se distribuye bajo la licencia MIT. Ver [LICENSE](LICENSE).

El juego original **Insomnia** es propiedad de **Mcryx Studios**. Los assets del juego (imagenes, audio, guion) pertenecen a sus respectivos autores. Este es un port no oficial sin fines de lucro realizado con fines educativos y de preservacion.

DDLC-LOVE y LuaPlayer PS3 estan bajo sus respectivas licencias. Consultar sus repositorios para mas informacion.

---

Port realizado con fines educativos y de preservacion de software.
Si disfrutas el juego, apoya al creador original en [itch.io](https://mcryxstudios.itch.io/insomnia-jeff-the-killer).
