#!/usr/bin/env python3
"""Builds the gbps.run static site into ./site from template.html.
Run: python3 build.py  → copy site/* to the repo root (Hostinger deploys the repo root into public_html)."""
import json, os, re, shutil, html, datetime

ROOT = "https://gbps.run"
OUT = "site"
TEMPLATE = open("template.html", encoding="utf-8").read()
ANALYTICS = "<!-- Analytics: paste your Cloudflare Web Analytics or Plausible snippet here -->"

# ----------------------------------------------------------------------------- UI strings
STR = {}
STR["en"] = dict(
    offline='offline', live_empty='Monitoring starts with the first test. Keep this tab open and the chart fills in through the day.', live_summary='<b>Last 24 h:</b> {uptime}% uptime · {n} checks · {drops} drops · download min {min} / avg {avg} / max {max} Mbps · last check {last}',
    settings="Settings", theme="Toggle dark or light theme", gauge_label="Speed gauge", phase_idle="Tap Start to run the test", start="Start test", stop="Stop",
    kbd="Press Space to start · ~25 seconds · no ads, no sign-up",
    download="Download", upload="Upload", ping="Ping", jitter="Jitter", loaded="Ping under load", loaded_sub="download / upload", bloat="Bufferbloat", bloat_sub="lag when busy",
    consistency="Consistency", cons_sub="how steady the speed is", loss="Packet loss",
    verdicts_h="What your connection can handle", verdicts_sub="based on this test",
    plan_h="Are you getting what you pay for?", plan_label="My plan is", plan_unit="Mbps download", wired="Wired",
    dl_h="How long things take at this speed", share_h="Share this result", copy_link="Copy result link", copy_summary="Copy summary", dl_image="Download result image", share_btn="Share…", again="Test again",
    hist_h="Your history", hist_sub="saved on this device only", monitor="Monitor every", off="off", csv="Copy as CSV", clear="Clear history",
    when="When", down_s="Down", up_s="Up", loaded_s="Loaded", bloat_s="Bloat", server="Server",
    duration="Duration", quick="Quick", standard="Standard", thorough="Thorough", units="Units", test_upload="Test upload", autostart="Auto-start on open", show_ip="Show my IP",
    settings_note="Test data is exchanged with Cloudflare's global network (speed.cloudflare.com), so the server is usually within a few hundred miles of you. Nothing about your test is uploaded anywhere except the random test bytes themselves.",
    more_h="More tests", embed_h="Put this test on your site", embed_p="Free to embed. Paste this where you want the test to appear:",
    footer="free · no ads, no tracking · results stay on your device", about="about", privacy="privacy",
    # JS
    ph_server="Finding the nearest server…", ph_ping="Measuring ping…", ph_down="Testing download…", ph_up="Testing upload…", ph_done="Done · {note} connection", ph_stopped="Test stopped", ph_failed="Test failed",
    err_offline="You appear to be offline. Check your connection and try again.",
    err_server="Could not reach the test servers. Check that you are online, then try again. (If this page is embedded in a sandbox or a strict corporate network, open it at its own address.)",
    ping_n=["excellent", "great for gaming", "fine for most things", "sluggish"],
    speed_n=["blazing fast", "very fast", "fast", "good", "basic", "slow"],
    jit_n=["very stable", "stable", "unstable"], loss_n=["no loss", "some packets lost"], cons_n=["rock steady", "steady", "fluctuating"],
    not_tested="not tested", up_not_tested="Upload not tested.", peak="peak",
    bloat_none="no lag when busy", bloat_notes=["", "+{d} ms when busy", "+{d} ms when busy", "+{d} ms – calls may stutter", "+{d} ms – noticeable lag", "+{d} ms – severe lag"],
    bloat_relay="measured through a relay/VPN — not your router",
    great="Great", ok="OK", weak="Weak",
    v=dict(stream=dict(t="4K streaming (Netflix, YouTube)", a="About {n} simultaneous 4K streams.", b="May drop to HD or buffer."),
           calls=dict(t="HD video calls (Zoom, FaceTime, Teams)", a="Sharp video, both ways.", b="Your video to others may look blocky.", c="Calls may freeze when the line is busy."),
           gaming=dict(t="Online gaming (PS5, Xbox, PC)", a="Low lag, even while others download.", b="Lag spikes when someone else downloads.", c="Playable, but not competitive-grade."),
           cloud=dict(t="Cloud gaming (GeForce Now, Xbox Cloud)", a="4K cloud gaming ready.", b="1080p should work; 4K may stutter."),
           wfh=dict(t="Working from home (VPN, screen share)", a="Smooth screen sharing and file syncs.", b="Screen sharing may look soft; big uploads are slow."),
           backup=dict(t="Uploading videos / cloud backup", a="A 5 GB video uploads in ~{t}."),
           house=dict(t="Busy household (10+ devices)", a="Everyone can stream, game and work at once.", b="Fine unless several people download at once.", c="Will feel crowded at peak times."),
           cams=dict(t="Smart home & security cameras", a="Several cameras can stream to the cloud.", b="Limit cloud cameras or lower their quality.")),
    dl=dict(movie4k="4K movie (15 GB)", game="100 GB game", phone="Phone update (7 GB)", photos="1,000 photos (4 GB)", album="Album (100 MB)", moviehd="HD movie (4 GB)", page="Web page (3 MB)", backup="Backup 50 GB (upload)"),
    plan=dict(p90="You're getting {pct}% of your {plan} Mbps plan. That's as good as it gets.", p70="You're getting {pct}% of your {plan} Mbps plan.", p70w="You're getting {pct}% of your {plan} Mbps plan over Wi‑Fi, which is normal.",
              p40="You're getting {pct}% of your {plan} Mbps plan. Worth investigating.", p40w="You're getting {pct}% of your {plan} Mbps plan. Wi‑Fi is probably the bottleneck.",
              p0="You're only getting {pct}% of your {plan} Mbps plan. Contact your provider if this repeats.", p0w="You're only getting {pct}% of your {plan} Mbps plan. Try a wired test before calling your provider.",
              enter="Enter your plan speed to see whether you're getting it.",
              a_room="Test in the same room as the router; walls cut Wi‑Fi speed fast.", a_band="Make sure your device is on the 5 GHz or 6 GHz band, not 2.4 GHz.", a_wifi6="For 500 Mbps+, you need a Wi‑Fi 6/6E/7 router with 160 MHz channels and a device that supports them.",
              a_cable="Try a different Ethernet cable (Cat 5e or better) and port.", a_restart="Restart the modem, then the router, and test again.", a_quiet="Test at a quiet time; if it is still low, ask your provider to check signal levels.",
              a_gig="Gigabit plans are often provisioned around 1.1–1.2 Gbps; a single gigabit Ethernet port tops out near 940 Mbps.",
              a_bloat="Bufferbloat grade {g}: enable SQM / \"Smart Queue\" or QoS on your router to stop lag when the line is busy.",
              a_jitter="High jitter: move closer to the router, or check for interference from neighbours' networks (change the channel).",
              a_loss="Packet loss detected: check cables and the coax connection; repeat the test a few times.",
              a_upload="Upload is much lower than download. That's typical for cable plans; fibre plans give equal upload if you need it.",
              nothing="Nothing to fix. Enjoy."),
    network="Network", protocol="Protocol", show_in_settings="show in settings",
    relay_notice="Looks like <b>iCloud Private Relay</b> (or a VPN) is on. Your traffic is going through a relay network, which caps speed and adds latency — this is true for <em>every</em> speed test in this browser, not just this one. For your real speed: System Settings → your name → iCloud → Private Relay → off, or test in a non-Safari browser.",
    relay_advice="iCloud Private Relay / VPN detected: results reflect the relay, not your home connection. Turn it off to test the real line.",
    share_text="My internet speed test (gbps.run)\n↓ {down} Mbps  ↑ {up} Mbps\nPing {ping} ms · Jitter {jitter} ms · Bufferbloat {bloat}\nServer: {server}{net}\n{url}",
    share_title="My internet speed", copied="Copied", copied_link="Link copied — it shows your result to whoever opens it", copy_fail="Copy not allowed here — select the text instead", cleared="History cleared", csv_copied="CSV copied",
    img_title="Internet speed test", shared_h="Someone shared their result with you:", shared_cta="Run the test to compare yours.",
    no_tests="No tests yet. Your results will appear here.", avg="avg", mon_status="Running a quick test every {min} min while this tab stays open.",
    fallback_server="fallback server", fallback_note="download-only fallback server used",
    out_checking="Checking your connection…", out_down="Your connection can't reach the internet right now. If other devices in your home are also offline, it's likely an outage on your provider's side.",
    out_up="Your connection is up: {ping} ms to the nearest server. If a specific service is failing, the problem is probably on their side.", out_slow="You're online but slow to respond ({ping} ms). Run the full test below to see what's going on.",
)

STR["es"] = dict(
    offline='sin conexión', live_empty='El monitoreo empieza con el primer test. Deja esta pestaña abierta y la gráfica se irá llenando durante el día.', live_summary='<b>Últimas 24 h:</b> {uptime}% disponible · {n} comprobaciones · {drops} caídas · descarga mín {min} / media {avg} / máx {max} Mbps · última {last}',
    settings="Ajustes", theme="Cambiar tema claro u oscuro", gauge_label="Medidor de velocidad", phase_idle="Pulsa Iniciar para hacer la prueba", start="Iniciar prueba", stop="Detener",
    kbd="Pulsa Espacio para iniciar · ~25 segundos · sin anuncios, sin registro",
    download="Descarga", upload="Subida", ping="Ping", jitter="Jitter", loaded="Ping con carga", loaded_sub="descarga / subida", bloat="Bufferbloat", bloat_sub="retraso cuando hay tráfico",
    consistency="Estabilidad", cons_sub="qué tan constante es la velocidad", loss="Pérdida de paquetes",
    verdicts_h="Qué puede hacer tu conexión", verdicts_sub="según esta prueba",
    plan_h="¿Recibes lo que pagas?", plan_label="Mi plan es de", plan_unit="Mbps de descarga", wired="Cable",
    dl_h="Cuánto tardan las cosas a esta velocidad", share_h="Compartir resultado", copy_link="Copiar enlace del resultado", copy_summary="Copiar resumen", dl_image="Descargar imagen", share_btn="Compartir…", again="Repetir prueba",
    hist_h="Tu historial", hist_sub="guardado solo en este dispositivo", monitor="Monitorear cada", off="no", csv="Copiar como CSV", clear="Borrar historial",
    when="Cuándo", down_s="Bajada", up_s="Subida", loaded_s="Con carga", bloat_s="Bloat", server="Servidor",
    duration="Duración", quick="Rápida", standard="Estándar", thorough="Completa", units="Unidades", test_upload="Probar subida", autostart="Iniciar al abrir", show_ip="Mostrar mi IP",
    settings_note="Los datos de prueba se intercambian con la red global de Cloudflare (speed.cloudflare.com), así que el servidor suele estar a pocos cientos de kilómetros. No se envía nada de tu prueba a ningún sitio, salvo los bytes aleatorios de la propia prueba.",
    more_h="Más pruebas", embed_h="Pon esta prueba en tu web", embed_p="Gratis para insertar. Pega esto donde quieras que aparezca la prueba:",
    footer="gratis · sin anuncios ni rastreo · los resultados se quedan en tu dispositivo", about="acerca de", privacy="privacidad",
    ph_server="Buscando el servidor más cercano…", ph_ping="Midiendo ping…", ph_down="Probando descarga…", ph_up="Probando subida…", ph_done="Listo · conexión {note}", ph_stopped="Prueba detenida", ph_failed="La prueba falló",
    err_offline="Parece que no tienes conexión. Revisa tu red e inténtalo de nuevo.",
    err_server="No se pudo conectar con los servidores de prueba. Comprueba que tienes internet e inténtalo de nuevo.",
    ping_n=["excelente", "ideal para juegos", "bien para casi todo", "lento"],
    speed_n=["ultrarrápida", "muy rápida", "rápida", "buena", "básica", "lenta"],
    jit_n=["muy estable", "estable", "inestable"], loss_n=["sin pérdida", "algunos paquetes perdidos"], cons_n=["muy constante", "constante", "fluctuante"],
    not_tested="no probada", up_not_tested="Subida no probada.", peak="pico",
    bloat_none="sin retraso con tráfico", bloat_notes=["", "+{d} ms con tráfico", "+{d} ms con tráfico", "+{d} ms – las llamadas pueden cortarse", "+{d} ms – retraso notable", "+{d} ms – retraso grave"],
    bloat_relay="medido a través de un relay/VPN — no es tu router",
    great="Excelente", ok="Aceptable", weak="Flojo",
    v=dict(stream=dict(t="Streaming 4K (Netflix, YouTube)", a="Unas {n} transmisiones 4K a la vez.", b="Puede bajar a HD o cargar."),
           calls=dict(t="Videollamadas HD (Zoom, FaceTime, Teams)", a="Vídeo nítido en ambos sentidos.", b="Tu vídeo puede verse pixelado.", c="Las llamadas pueden congelarse cuando hay tráfico."),
           gaming=dict(t="Juegos online (PS5, Xbox, PC)", a="Poco lag, incluso mientras otros descargan.", b="Picos de lag cuando alguien descarga.", c="Jugable, pero no a nivel competitivo."),
           cloud=dict(t="Juegos en la nube (GeForce Now, Xbox Cloud)", a="Listo para juegos en la nube en 4K.", b="1080p debería ir bien; 4K puede trabarse."),
           wfh=dict(t="Teletrabajo (VPN, compartir pantalla)", a="Pantalla compartida y sincronización fluidas.", b="La pantalla compartida puede verse borrosa; las subidas grandes son lentas."),
           backup=dict(t="Subir vídeos / copias en la nube", a="Un vídeo de 5 GB se sube en ~{t}."),
           house=dict(t="Casa con muchos dispositivos (10+)", a="Todos pueden ver, jugar y trabajar a la vez.", b="Bien, salvo que varios descarguen a la vez.", c="Se notará saturada en horas punta."),
           cams=dict(t="Domótica y cámaras de seguridad", a="Varias cámaras pueden transmitir a la nube.", b="Limita las cámaras en la nube o baja su calidad.")),
    dl=dict(movie4k="Película 4K (15 GB)", game="Juego de 100 GB", phone="Actualización del móvil (7 GB)", photos="1.000 fotos (4 GB)", album="Álbum (100 MB)", moviehd="Película HD (4 GB)", page="Página web (3 MB)", backup="Copia de 50 GB (subida)"),
    plan=dict(p90="Recibes el {pct}% de tu plan de {plan} Mbps. No se puede pedir más.", p70="Recibes el {pct}% de tu plan de {plan} Mbps.", p70w="Recibes el {pct}% de tu plan de {plan} Mbps por Wi‑Fi, lo cual es normal.",
              p40="Recibes el {pct}% de tu plan de {plan} Mbps. Conviene investigar.", p40w="Recibes el {pct}% de tu plan de {plan} Mbps. El Wi‑Fi es probablemente el cuello de botella.",
              p0="Solo recibes el {pct}% de tu plan de {plan} Mbps. Contacta con tu operador si se repite.", p0w="Solo recibes el {pct}% de tu plan de {plan} Mbps. Prueba por cable antes de llamar a tu operador.",
              enter="Introduce la velocidad de tu plan para ver si la recibes.",
              a_room="Prueba en la misma habitación que el router; las paredes reducen mucho el Wi‑Fi.", a_band="Asegúrate de usar la banda de 5 GHz o 6 GHz, no la de 2,4 GHz.", a_wifi6="Para más de 500 Mbps necesitas un router Wi‑Fi 6/6E/7 con canales de 160 MHz y un dispositivo compatible.",
              a_cable="Prueba otro cable Ethernet (Cat 5e o mejor) y otro puerto.", a_restart="Reinicia el módem y luego el router, y vuelve a probar.", a_quiet="Prueba en una hora tranquila; si sigue bajo, pide a tu operador que revise la señal.",
              a_gig="Los planes gigabit suelen entregar 1,1–1,2 Gbps; un puerto Ethernet gigabit llega como máximo a unos 940 Mbps.",
              a_bloat="Bufferbloat grado {g}: activa SQM / \"Smart Queue\" o QoS en tu router para evitar el lag cuando hay tráfico.",
              a_jitter="Jitter alto: acércate al router o revisa interferencias de redes vecinas (cambia el canal).",
              a_loss="Se detectó pérdida de paquetes: revisa cables y conexiones; repite la prueba varias veces.",
              a_upload="La subida es mucho menor que la bajada. Es normal en cable; la fibra ofrece subida simétrica si la necesitas.",
              nothing="Nada que arreglar. Disfruta."),
    network="Red", protocol="Protocolo", show_in_settings="ver en ajustes",
    relay_notice="Parece que <b>iCloud Private Relay</b> (o una VPN) está activo. Tu tráfico pasa por una red intermedia que limita la velocidad y añade latencia — afecta a <em>todas</em> las pruebas en este navegador. Para tu velocidad real: Ajustes → tu nombre → iCloud → Private Relay → desactivar, o prueba en otro navegador.",
    relay_advice="iCloud Private Relay / VPN detectado: los resultados reflejan el relay, no tu conexión. Desactívalo para probar la línea real.",
    share_text="Mi prueba de velocidad (gbps.run)\n↓ {down} Mbps  ↑ {up} Mbps\nPing {ping} ms · Jitter {jitter} ms · Bufferbloat {bloat}\nServidor: {server}{net}\n{url}",
    share_title="Mi velocidad de internet", copied="Copiado", copied_link="Enlace copiado — muestra tu resultado a quien lo abra", copy_fail="No se pudo copiar — selecciona el texto", cleared="Historial borrado", csv_copied="CSV copiado",
    img_title="Prueba de velocidad", shared_h="Alguien compartió su resultado contigo:", shared_cta="Haz la prueba para comparar el tuyo.",
    no_tests="Aún no hay pruebas. Tus resultados aparecerán aquí.", avg="media", mon_status="Prueba rápida cada {min} min mientras esta pestaña siga abierta.",
    fallback_server="servidor alternativo", fallback_note="se usó un servidor alternativo (solo descarga)",
    out_checking="Comprobando tu conexión…", out_down="Tu conexión no llega a internet ahora mismo. Si otros dispositivos de tu casa tampoco tienen conexión, probablemente es una caída de tu operador.",
    out_up="Tu conexión funciona: {ping} ms al servidor más cercano. Si un servicio concreto falla, el problema está probablemente en su lado.", out_slow="Tienes conexión pero responde lento ({ping} ms). Haz la prueba completa para ver qué pasa.",
)

STR["pt"] = dict(
    offline='offline', live_empty='O monitoramento começa com o primeiro teste. Deixe esta aba aberta e o gráfico vai se preenchendo ao longo do dia.', live_summary='<b>Últimas 24 h:</b> {uptime}% no ar · {n} verificações · {drops} quedas · download mín {min} / média {avg} / máx {max} Mbps · última {last}',
    settings="Configurações", theme="Alternar tema claro ou escuro", gauge_label="Medidor de velocidade", phase_idle="Toque em Iniciar para fazer o teste", start="Iniciar teste", stop="Parar",
    kbd="Pressione Espaço para iniciar · ~25 segundos · sem anúncios, sem cadastro",
    download="Download", upload="Upload", ping="Ping", jitter="Jitter", loaded="Ping sob carga", loaded_sub="download / upload", bloat="Bufferbloat", bloat_sub="atraso com tráfego",
    consistency="Estabilidade", cons_sub="quão constante é a velocidade", loss="Perda de pacotes",
    verdicts_h="O que sua conexão aguenta", verdicts_sub="com base neste teste",
    plan_h="Você recebe o que paga?", plan_label="Meu plano é de", plan_unit="Mbps de download", wired="Cabo",
    dl_h="Quanto tempo as coisas levam nesta velocidade", share_h="Compartilhar resultado", copy_link="Copiar link do resultado", copy_summary="Copiar resumo", dl_image="Baixar imagem", share_btn="Compartilhar…", again="Testar de novo",
    hist_h="Seu histórico", hist_sub="salvo só neste dispositivo", monitor="Monitorar a cada", off="não", csv="Copiar como CSV", clear="Limpar histórico",
    when="Quando", down_s="Down", up_s="Up", loaded_s="Sob carga", bloat_s="Bloat", server="Servidor",
    duration="Duração", quick="Rápido", standard="Padrão", thorough="Completo", units="Unidades", test_upload="Testar upload", autostart="Iniciar ao abrir", show_ip="Mostrar meu IP",
    settings_note="Os dados do teste são trocados com a rede global da Cloudflare (speed.cloudflare.com), então o servidor costuma estar a poucas centenas de quilômetros. Nada do seu teste é enviado a lugar nenhum, além dos bytes aleatórios do próprio teste.",
    more_h="Mais testes", embed_h="Coloque este teste no seu site", embed_p="Grátis para incorporar. Cole isto onde quiser que o teste apareça:",
    footer="grátis · sem anúncios nem rastreamento · os resultados ficam no seu dispositivo", about="sobre", privacy="privacidade",
    ph_server="Procurando o servidor mais próximo…", ph_ping="Medindo ping…", ph_down="Testando download…", ph_up="Testando upload…", ph_done="Pronto · conexão {note}", ph_stopped="Teste interrompido", ph_failed="O teste falhou",
    err_offline="Parece que você está offline. Verifique sua conexão e tente de novo.",
    err_server="Não foi possível alcançar os servidores de teste. Verifique se você está online e tente de novo.",
    ping_n=["excelente", "ótimo para jogos", "bom para quase tudo", "lento"],
    speed_n=["ultrarrápida", "muito rápida", "rápida", "boa", "básica", "lenta"],
    jit_n=["muito estável", "estável", "instável"], loss_n=["sem perda", "alguns pacotes perdidos"], cons_n=["muito constante", "constante", "oscilando"],
    not_tested="não testado", up_not_tested="Upload não testado.", peak="pico",
    bloat_none="sem atraso com tráfego", bloat_notes=["", "+{d} ms com tráfego", "+{d} ms com tráfego", "+{d} ms – chamadas podem travar", "+{d} ms – atraso perceptível", "+{d} ms – atraso grave"],
    bloat_relay="medido através de relay/VPN — não é o seu roteador",
    great="Ótimo", ok="OK", weak="Fraco",
    v=dict(stream=dict(t="Streaming 4K (Netflix, YouTube)", a="Cerca de {n} streams 4K ao mesmo tempo.", b="Pode cair para HD ou travar."),
           calls=dict(t="Videochamadas HD (Zoom, FaceTime, Teams)", a="Vídeo nítido nos dois sentidos.", b="Seu vídeo pode ficar pixelado para os outros.", c="Chamadas podem congelar quando há tráfego."),
           gaming=dict(t="Jogos online (PS5, Xbox, PC)", a="Pouco lag, mesmo com outros baixando.", b="Picos de lag quando alguém baixa algo.", c="Jogável, mas não em nível competitivo."),
           cloud=dict(t="Jogos na nuvem (GeForce Now, Xbox Cloud)", a="Pronto para jogos na nuvem em 4K.", b="1080p deve funcionar; 4K pode travar."),
           wfh=dict(t="Home office (VPN, compartilhar tela)", a="Compartilhamento de tela e sincronização fluidos.", b="A tela compartilhada pode ficar borrada; uploads grandes são lentos."),
           backup=dict(t="Enviar vídeos / backup na nuvem", a="Um vídeo de 5 GB sobe em ~{t}."),
           house=dict(t="Casa com muitos aparelhos (10+)", a="Todos podem assistir, jogar e trabalhar ao mesmo tempo.", b="Bom, a menos que vários baixem ao mesmo tempo.", c="Vai ficar congestionado nos horários de pico."),
           cams=dict(t="Casa inteligente e câmeras", a="Várias câmeras podem transmitir para a nuvem.", b="Limite as câmeras na nuvem ou reduza a qualidade.")),
    dl=dict(movie4k="Filme 4K (15 GB)", game="Jogo de 100 GB", phone="Atualização do celular (7 GB)", photos="1.000 fotos (4 GB)", album="Álbum (100 MB)", moviehd="Filme HD (4 GB)", page="Página web (3 MB)", backup="Backup de 50 GB (upload)"),
    plan=dict(p90="Você recebe {pct}% do seu plano de {plan} Mbps. Melhor impossível.", p70="Você recebe {pct}% do seu plano de {plan} Mbps.", p70w="Você recebe {pct}% do seu plano de {plan} Mbps pelo Wi‑Fi, o que é normal.",
              p40="Você recebe {pct}% do seu plano de {plan} Mbps. Vale investigar.", p40w="Você recebe {pct}% do seu plano de {plan} Mbps. O Wi‑Fi provavelmente é o gargalo.",
              p0="Você recebe só {pct}% do seu plano de {plan} Mbps. Fale com a operadora se isso se repetir.", p0w="Você recebe só {pct}% do seu plano de {plan} Mbps. Teste no cabo antes de ligar para a operadora.",
              enter="Digite a velocidade do seu plano para ver se você a recebe.",
              a_room="Teste no mesmo cômodo do roteador; paredes derrubam o Wi‑Fi rapidamente.", a_band="Use a banda de 5 GHz ou 6 GHz, não a de 2,4 GHz.", a_wifi6="Para mais de 500 Mbps você precisa de um roteador Wi‑Fi 6/6E/7 com canais de 160 MHz e um aparelho compatível.",
              a_cable="Tente outro cabo Ethernet (Cat 5e ou melhor) e outra porta.", a_restart="Reinicie o modem, depois o roteador, e teste de novo.", a_quiet="Teste em um horário tranquilo; se continuar baixo, peça à operadora para verificar o sinal.",
              a_gig="Planos gigabit costumam entregar 1,1–1,2 Gbps; uma porta Ethernet gigabit chega no máximo a uns 940 Mbps.",
              a_bloat="Bufferbloat nota {g}: ative SQM / \"Smart Queue\" ou QoS no roteador para evitar lag com tráfego.",
              a_jitter="Jitter alto: aproxime-se do roteador ou verifique interferência de redes vizinhas (mude o canal).",
              a_loss="Perda de pacotes detectada: verifique cabos e conexões; repita o teste algumas vezes.",
              a_upload="O upload é bem menor que o download. É normal em cabo; fibra oferece upload simétrico se você precisar.",
              nothing="Nada para corrigir. Aproveite."),
    network="Rede", protocol="Protocolo", show_in_settings="ver nas configurações",
    relay_notice="Parece que o <b>iCloud Private Relay</b> (ou uma VPN) está ativo. Seu tráfego passa por uma rede intermediária que limita a velocidade e aumenta a latência — isso afeta <em>todos</em> os testes neste navegador. Para a velocidade real: Ajustes → seu nome → iCloud → Private Relay → desativar, ou teste em outro navegador.",
    relay_advice="iCloud Private Relay / VPN detectado: os resultados refletem o relay, não sua conexão. Desative para testar a linha real.",
    share_text="Meu teste de velocidade (gbps.run)\n↓ {down} Mbps  ↑ {up} Mbps\nPing {ping} ms · Jitter {jitter} ms · Bufferbloat {bloat}\nServidor: {server}{net}\n{url}",
    share_title="Minha velocidade de internet", copied="Copiado", copied_link="Link copiado — mostra seu resultado a quem abrir", copy_fail="Não foi possível copiar — selecione o texto", cleared="Histórico limpo", csv_copied="CSV copiado",
    img_title="Teste de velocidade", shared_h="Alguém compartilhou o resultado com você:", shared_cta="Faça o teste para comparar o seu.",
    no_tests="Nenhum teste ainda. Seus resultados aparecerão aqui.", avg="média", mon_status="Teste rápido a cada {min} min enquanto esta aba estiver aberta.",
    fallback_server="servidor alternativo", fallback_note="servidor alternativo usado (só download)",
    out_checking="Verificando sua conexão…", out_down="Sua conexão não alcança a internet agora. Se outros aparelhos da casa também estão offline, provavelmente é uma queda da operadora.",
    out_up="Sua conexão está no ar: {ping} ms até o servidor mais próximo. Se um serviço específico está falhando, o problema provavelmente é do lado deles.", out_slow="Você está online, mas respondendo devagar ({ping} ms). Faça o teste completo abaixo para entender.",
)


STR["hi"] = dict(
    offline='ऑफ़लाइन', live_empty='पहले टेस्ट के साथ मॉनिटरिंग शुरू होगी। यह टैब खुला रखें, दिन भर चार्ट भरता जाएगा।', live_summary='<b>पिछले 24 घंटे:</b> {uptime}% अपटाइम · {n} जाँच · {drops} ड्रॉप · डाउनलोड न्यूनतम {min} / औसत {avg} / अधिकतम {max} Mbps · आख़िरी जाँच {last}',
    settings="सेटिंग्स", theme="डार्क या लाइट थीम बदलें", gauge_label="स्पीड मीटर", phase_idle="टेस्ट शुरू करने के लिए Start दबाएँ", start="टेस्ट शुरू करें", stop="रोकें",
    kbd="Space दबाकर शुरू करें · ~25 सेकंड · कोई विज्ञापन नहीं, कोई साइन-अप नहीं",
    download="डाउनलोड", upload="अपलोड", ping="पिंग", jitter="जिटर", loaded="लोड के साथ पिंग", loaded_sub="डाउनलोड / अपलोड", bloat="बफरब्लोट", bloat_sub="ट्रैफ़िक के समय लैग",
    consistency="स्थिरता", cons_sub="स्पीड कितनी स्थिर है", loss="पैकेट लॉस",
    verdicts_h="आपका कनेक्शन क्या-क्या संभाल सकता है", verdicts_sub="इस टेस्ट के आधार पर",
    plan_h="क्या आपको वही स्पीड मिल रही है जिसका आप भुगतान करते हैं?", plan_label="मेरा प्लान है", plan_unit="Mbps डाउनलोड", wired="केबल (LAN)",
    dl_h="इस स्पीड पर चीज़ों में कितना समय लगेगा", share_h="यह रिज़ल्ट शेयर करें", copy_link="रिज़ल्ट लिंक कॉपी करें", copy_summary="सारांश कॉपी करें", dl_image="रिज़ल्ट इमेज डाउनलोड करें", share_btn="शेयर करें…", again="फिर से टेस्ट करें",
    hist_h="आपका इतिहास", hist_sub="सिर्फ़ इसी डिवाइस पर सेव", monitor="हर", off="बंद", csv="CSV कॉपी करें", clear="इतिहास मिटाएँ",
    when="कब", down_s="डाउन", up_s="अप", loaded_s="लोड पर", bloat_s="ब्लोट", server="सर्वर",
    duration="अवधि", quick="तेज़", standard="सामान्य", thorough="पूरा", units="इकाई", test_upload="अपलोड टेस्ट करें", autostart="खोलते ही शुरू करें", show_ip="मेरा IP दिखाएँ",
    settings_note="टेस्ट डेटा Cloudflare के ग्लोबल नेटवर्क (speed.cloudflare.com) से आदान-प्रदान होता है, इसलिए सर्वर आमतौर पर आपसे कुछ सौ किलोमीटर के भीतर होता है। टेस्ट के रैंडम बाइट्स के अलावा आपका कोई डेटा कहीं नहीं भेजा जाता।",
    more_h="और टेस्ट", embed_h="यह टेस्ट अपनी वेबसाइट पर लगाएँ", embed_p="मुफ़्त में एम्बेड करें। जहाँ टेस्ट दिखाना हो वहाँ यह पेस्ट करें:",
    footer="मुफ़्त · कोई विज्ञापन या ट्रैकिंग नहीं · रिज़ल्ट आपके डिवाइस पर ही रहते हैं", about="परिचय", privacy="प्राइवेसी",
    ph_server="नज़दीकी सर्वर खोजा जा रहा है…", ph_ping="पिंग मापा जा रहा है…", ph_down="डाउनलोड टेस्ट हो रहा है…", ph_up="अपलोड टेस्ट हो रहा है…", ph_done="पूरा · {note} कनेक्शन", ph_stopped="टेस्ट रोका गया", ph_failed="टेस्ट फेल हो गया",
    err_offline="लगता है आप ऑफ़लाइन हैं। कनेक्शन जाँचें और फिर कोशिश करें।",
    err_server="टेस्ट सर्वर तक पहुँच नहीं हो पाई। जाँचें कि इंटरनेट चल रहा है और फिर कोशिश करें।",
    ping_n=["बेहतरीन", "गेमिंग के लिए शानदार", "ज़्यादातर कामों के लिए ठीक", "धीमा"],
    speed_n=["बहुत ही तेज़", "बहुत तेज़", "तेज़", "अच्छा", "बेसिक", "धीमा"],
    jit_n=["बहुत स्थिर", "स्थिर", "अस्थिर"], loss_n=["कोई लॉस नहीं", "कुछ पैकेट खोए"], cons_n=["एकदम स्थिर", "स्थिर", "उतार-चढ़ाव"],
    not_tested="टेस्ट नहीं हुआ", up_not_tested="अपलोड टेस्ट नहीं हुआ।", peak="अधिकतम",
    bloat_none="ट्रैफ़िक में भी कोई लैग नहीं", bloat_notes=["", "ट्रैफ़िक में +{d} ms", "ट्रैफ़िक में +{d} ms", "+{d} ms – कॉल अटक सकती हैं", "+{d} ms – साफ़ लैग", "+{d} ms – गंभीर लैग"],
    bloat_relay="रिले/VPN के ज़रिए मापा गया — यह आपके राउटर की समस्या नहीं",
    great="बढ़िया", ok="ठीक", weak="कमज़ोर",
    v=dict(stream=dict(t="4K स्ट्रीमिंग (Netflix, YouTube, Hotstar)", a="लगभग {n} 4K स्ट्रीम एक साथ।", b="HD पर गिर सकता है या बफर हो सकता है।"),
           calls=dict(t="HD वीडियो कॉल (Zoom, Teams, Google Meet)", a="दोनों तरफ़ साफ़ वीडियो।", b="दूसरों को आपका वीडियो धुंधला दिख सकता है।", c="ट्रैफ़िक के समय कॉल अटक सकती हैं।"),
           gaming=dict(t="ऑनलाइन गेमिंग (BGMI, Free Fire, PS5, PC)", a="कम लैग, तब भी जब दूसरे डाउनलोड कर रहे हों।", b="जब कोई और डाउनलोड करे तो लैग बढ़ता है।", c="खेलने लायक, पर कॉम्पिटिटिव लेवल का नहीं।"),
           cloud=dict(t="क्लाउड गेमिंग (GeForce Now, Xbox Cloud)", a="4K क्लाउड गेमिंग के लिए तैयार।", b="1080p चलना चाहिए; 4K अटक सकता है।"),
           wfh=dict(t="वर्क फ्रॉम होम (VPN, स्क्रीन शेयर)", a="स्क्रीन शेयर और फ़ाइल सिंक स्मूद।", b="स्क्रीन शेयर धुंधला दिख सकता है; बड़े अपलोड धीमे होंगे।"),
           backup=dict(t="वीडियो अपलोड / क्लाउड बैकअप", a="5 GB का वीडियो ~{t} में अपलोड होगा।"),
           house=dict(t="बड़ा परिवार (10+ डिवाइस)", a="सब एक साथ स्ट्रीम, गेम और काम कर सकते हैं।", b="ठीक है, जब तक कई लोग एक साथ डाउनलोड न करें।", c="पीक समय पर भीड़ महसूस होगी।"),
           cams=dict(t="स्मार्ट होम और CCTV कैमरे", a="कई कैमरे क्लाउड पर स्ट्रीम कर सकते हैं।", b="क्लाउड कैमरे कम रखें या क्वालिटी घटाएँ।")),
    dl=dict(movie4k="4K फ़िल्म (15 GB)", game="100 GB गेम", phone="फ़ोन अपडेट (7 GB)", photos="1,000 फ़ोटो (4 GB)", album="एल्बम (100 MB)", moviehd="HD फ़िल्म (4 GB)", page="वेब पेज (3 MB)", backup="50 GB बैकअप (अपलोड)"),
    plan=dict(p90="आपको अपने {plan} Mbps प्लान का {pct}% मिल रहा है। इससे बेहतर नहीं हो सकता।", p70="आपको अपने {plan} Mbps प्लान का {pct}% मिल रहा है।", p70w="Wi‑Fi पर आपको अपने {plan} Mbps प्लान का {pct}% मिल रहा है, जो सामान्य है।",
              p40="आपको अपने {plan} Mbps प्लान का {pct}% मिल रहा है। जाँच करने लायक है।", p40w="आपको अपने {plan} Mbps प्लान का {pct}% मिल रहा है। शायद Wi‑Fi ही रुकावट है।",
              p0="आपको अपने {plan} Mbps प्लान का सिर्फ़ {pct}% मिल रहा है। बार-बार हो तो प्रोवाइडर से बात करें।", p0w="आपको अपने {plan} Mbps प्लान का सिर्फ़ {pct}% मिल रहा है। प्रोवाइडर को कॉल करने से पहले LAN केबल से टेस्ट करें।",
              enter="अपने प्लान की स्पीड डालें और देखें कि वह मिल रही है या नहीं।",
              a_room="राउटर वाले कमरे में टेस्ट करें; दीवारें Wi‑Fi स्पीड तेज़ी से घटाती हैं।", a_band="पक्का करें कि डिवाइस 5 GHz या 6 GHz बैंड पर है, 2.4 GHz पर नहीं।", a_wifi6="500 Mbps+ के लिए Wi‑Fi 6/6E/7 राउटर (160 MHz चैनल) और उसे सपोर्ट करने वाला डिवाइस चाहिए।",
              a_cable="दूसरा Ethernet केबल (Cat 5e या बेहतर) और दूसरा पोर्ट आज़माएँ।", a_restart="पहले मॉडम, फिर राउटर रीस्टार्ट करें और दोबारा टेस्ट करें।", a_quiet="शांत समय पर टेस्ट करें; फिर भी कम हो तो प्रोवाइडर से सिग्नल जाँचने को कहें।",
              a_gig="गीगाबिट प्लान अक्सर 1.1–1.2 Gbps देते हैं; एक गीगाबिट Ethernet पोर्ट अधिकतम ~940 Mbps देता है।",
              a_bloat="बफरब्लोट ग्रेड {g}: ट्रैफ़िक के समय लैग रोकने के लिए राउटर में SQM / \"Smart Queue\" या QoS चालू करें।",
              a_jitter="जिटर ज़्यादा है: राउटर के पास जाएँ या पड़ोसी नेटवर्क के इंटरफ़ेरेंस की जाँच करें (चैनल बदलें)।",
              a_loss="पैकेट लॉस मिला: केबल और कनेक्शन जाँचें; टेस्ट कुछ बार दोहराएँ।",
              a_upload="अपलोड, डाउनलोड से बहुत कम है। केबल/4G प्लान में यह सामान्य है; ज़रूरत हो तो फ़ाइबर में अपलोड बराबर मिलता है।",
              nothing="कुछ ठीक करने की ज़रूरत नहीं। मज़े करें।"),
    network="नेटवर्क", protocol="प्रोटोकॉल", show_in_settings="सेटिंग्स में देखें",
    relay_notice="लगता है <b>iCloud Private Relay</b> (या VPN) चालू है। आपका ट्रैफ़िक एक रिले नेटवर्क से जा रहा है जो स्पीड सीमित करता है और लेटेंसी बढ़ाता है — यह इस ब्राउज़र के <em>हर</em> स्पीड टेस्ट पर लागू होता है। असली स्पीड के लिए: Settings → आपका नाम → iCloud → Private Relay → बंद, या किसी दूसरे ब्राउज़र में टेस्ट करें।",
    relay_advice="iCloud Private Relay / VPN मिला: रिज़ल्ट रिले के हैं, आपके कनेक्शन के नहीं। असली लाइन टेस्ट करने के लिए इसे बंद करें।",
    share_text="मेरा इंटरनेट स्पीड टेस्ट (gbps.run)\n↓ {down} Mbps  ↑ {up} Mbps\nपिंग {ping} ms · जिटर {jitter} ms · बफरब्लोट {bloat}\nसर्वर: {server}{net}\n{url}",
    share_title="मेरी इंटरनेट स्पीड", copied="कॉपी हो गया", copied_link="लिंक कॉपी हो गया — जो खोलेगा उसे आपका रिज़ल्ट दिखेगा", copy_fail="कॉपी नहीं हो सका — टेक्स्ट सिलेक्ट करें", cleared="इतिहास मिटा दिया", csv_copied="CSV कॉपी हो गया",
    img_title="इंटरनेट स्पीड टेस्ट", shared_h="किसी ने आपके साथ अपना रिज़ल्ट शेयर किया:", shared_cta="अपना रिज़ल्ट तुलना के लिए टेस्ट करें।",
    no_tests="अभी कोई टेस्ट नहीं। आपके रिज़ल्ट यहाँ दिखेंगे।", avg="औसत", mon_status="जब तक यह टैब खुला है, हर {min} मिनट पर एक क्विक टेस्ट चलेगा।",
    fallback_server="वैकल्पिक सर्वर", fallback_note="वैकल्पिक सर्वर (सिर्फ़ डाउनलोड) इस्तेमाल हुआ",
    out_checking="आपका कनेक्शन जाँचा जा रहा है…", out_down="आपका कनेक्शन अभी इंटरनेट तक नहीं पहुँच पा रहा। अगर घर के दूसरे डिवाइस भी ऑफ़लाइन हैं, तो शायद प्रोवाइडर की तरफ़ से आउटेज है।",
    out_up="आपका कनेक्शन चालू है: नज़दीकी सर्वर तक {ping} ms। अगर कोई खास ऐप/सर्विस नहीं चल रही, तो समस्या शायद उनकी तरफ़ है।", out_slow="आप ऑनलाइन हैं पर रिस्पॉन्स धीमा है ({ping} ms)। नीचे पूरा टेस्ट चलाकर देखें।",
)

OG_LOCALE = {"en": "en_US", "es": "es_ES", "pt": "pt_BR", "hi": "hi_IN"}
LANG_NAMES = {"en": "English", "es": "Español", "pt": "Português", "hi": "हिन्दी"}

# ----------------------------------------------------------------------------- FAQ content
def faq_html(faqs):
    return "\n".join(f'      <details{" open" if i == 0 else ""}><summary>{html.escape(q)}</summary><p>{a}</p></details>' for i, (q, a) in enumerate(faqs))
def faq_json(faqs):
    return ",".join(json.dumps({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}}, ensure_ascii=False) for q, a in faqs)

GENERIC_FAQ = {
 "en": [
    ("What is a good internet speed?", "For one person, 25–50 Mbps download covers 4K streaming and video calls. A household with several people streaming, gaming and working from home is comfortable at 100–300 Mbps. Upload matters more than most people think: 10 Mbps or more keeps video calls sharp and lets backups finish."),
    ("Why is my Wi‑Fi slower than my plan?", "Wi‑Fi loses speed through walls and distance, shares airtime with neighbours, and older devices cap the link. Test in the same room as the router, use the 5 GHz or 6 GHz band, and compare with a wired test to see whether the limit is Wi‑Fi or your provider. On a gigabit plan, 800–940 Mbps on Wi‑Fi is excellent."),
    ("What is bufferbloat and why does it matter?", "Bufferbloat is the rise in ping when your connection is busy, for example during a big download. It's why video calls freeze when someone else starts a backup. We measure ping while loading the line and grade the increase: A means almost no change, F means hundreds of milliseconds. Routers with SQM or \"smart queue\" settings fix it."),
    ("Why do different speed tests give different numbers?", "Tests use different servers, open a different number of parallel connections and average differently. Single-connection tests often read low on fast plans. VPNs and iCloud Private Relay cap every test in that browser. Compare trends over a few runs rather than one number."),
    ("What do ping and jitter mean?", "Ping is the round-trip time to the server. Under 20 ms is excellent, under 50 ms is great for gaming, and 100 ms+ feels sluggish. Jitter is how much ping varies; low jitter keeps calls and games smooth."),
    ("How accurate is this test?", "It opens up to eight parallel connections to Cloudflare's nearest data centre (usually within a few hundred miles of you), ignores the first two seconds of ramp-up and averages the steady state. That mirrors how Ookla-style tests work and reads correctly on gigabit plans. Over about 2.5 Gbps the browser itself becomes the bottleneck."),
 ],
 "es": [
    ("¿Qué velocidad de internet es buena?", "Para una persona, 25–50 Mbps de descarga cubren streaming 4K y videollamadas. Una casa con varias personas viendo series, jugando y teletrabajando está cómoda con 100–300 Mbps. La subida importa más de lo que parece: 10 Mbps o más mantienen las videollamadas nítidas."),
    ("¿Por qué mi Wi‑Fi es más lento que mi plan?", "El Wi‑Fi pierde velocidad con paredes y distancia, comparte el aire con los vecinos y los dispositivos antiguos limitan el enlace. Prueba en la misma habitación que el router, usa la banda de 5 GHz o 6 GHz y compara con una prueba por cable para saber si el límite es el Wi‑Fi o el operador."),
    ("¿Qué es el bufferbloat?", "Es el aumento del ping cuando la conexión está ocupada, por ejemplo durante una descarga grande. Por eso las videollamadas se congelan cuando alguien empieza una copia de seguridad. Medimos el ping mientras cargamos la línea y calificamos el aumento: A significa casi sin cambio, F cientos de milisegundos. Los routers con SQM o \"Smart Queue\" lo corrigen."),
    ("¿Por qué cada test de velocidad da un número distinto?", "Cada test usa servidores distintos, abre un número diferente de conexiones y promedia de otra forma. Los tests de una sola conexión suelen dar bajo en planes rápidos. Las VPN e iCloud Private Relay limitan todos los tests en ese navegador."),
    ("¿Qué significan ping y jitter?", "El ping es el tiempo de ida y vuelta al servidor. Menos de 20 ms es excelente, menos de 50 ms es ideal para juegos y más de 100 ms se nota lento. El jitter es cuánto varía el ping; un jitter bajo mantiene llamadas y juegos fluidos."),
    ("¿Qué tan preciso es este test?", "Abre hasta ocho conexiones en paralelo con el centro de datos de Cloudflare más cercano, ignora los dos primeros segundos de arranque y promedia el estado estable. Es el mismo método que usan los tests tipo Ookla y mide bien en planes gigabit."),
 ],
 "pt": [
    ("Qual é uma boa velocidade de internet?", "Para uma pessoa, 25–50 Mbps de download cobrem streaming 4K e videochamadas. Uma casa com várias pessoas assistindo, jogando e trabalhando fica confortável com 100–300 Mbps. O upload importa mais do que parece: 10 Mbps ou mais mantêm as videochamadas nítidas."),
    ("Por que meu Wi‑Fi é mais lento que meu plano?", "O Wi‑Fi perde velocidade com paredes e distância, divide o ar com os vizinhos e aparelhos antigos limitam o link. Teste no mesmo cômodo do roteador, use a banda de 5 GHz ou 6 GHz e compare com um teste no cabo para saber se o limite é o Wi‑Fi ou a operadora."),
    ("O que é bufferbloat?", "É o aumento do ping quando a conexão está ocupada, por exemplo durante um download grande. É por isso que videochamadas travam quando alguém começa um backup. Medimos o ping enquanto carregamos a linha e damos uma nota: A é quase sem mudança, F são centenas de milissegundos. Roteadores com SQM ou \"Smart Queue\" corrigem isso."),
    ("Por que cada teste de velocidade dá um número diferente?", "Cada teste usa servidores diferentes, abre um número diferente de conexões e calcula a média de outro jeito. Testes de conexão única costumam dar baixo em planos rápidos. VPNs e o iCloud Private Relay limitam todos os testes naquele navegador."),
    ("O que significam ping e jitter?", "Ping é o tempo de ida e volta até o servidor. Abaixo de 20 ms é excelente, abaixo de 50 ms é ótimo para jogos e acima de 100 ms parece lento. Jitter é o quanto o ping varia; jitter baixo mantém chamadas e jogos fluidos."),
    ("Este teste é preciso?", "Ele abre até oito conexões em paralelo com o data center da Cloudflare mais próximo, ignora os dois primeiros segundos de aceleração e calcula a média do estado estável. É o mesmo método dos testes tipo Ookla e mede corretamente em planos gigabit."),
 ],
 "hi": [
    ("अच्छी इंटरनेट स्पीड कितनी होती है?", "एक व्यक्ति के लिए 25–50 Mbps डाउनलोड 4K स्ट्रीमिंग और वीडियो कॉल के लिए काफ़ी है। जिस घर में कई लोग स्ट्रीम, गेम और वर्क फ्रॉम होम करते हैं, वहाँ 100–300 Mbps आरामदायक है। अपलोड जितना लोग सोचते हैं उससे ज़्यादा मायने रखता है: 10 Mbps या ज़्यादा से वीडियो कॉल साफ़ रहती हैं।"),
    ("मेरा Wi‑Fi मेरे प्लान से धीमा क्यों है?", "दीवारें और दूरी सिग्नल घटाती हैं, 2.4 GHz बैंड धीमा और भीड़ वाला है, और पुराने राउटर/डिवाइस लिंक को सीमित करते हैं। राउटर वाले कमरे में टेस्ट करें, 5 GHz या 6 GHz बैंड इस्तेमाल करें, और LAN केबल से तुलना करें ताकि पता चले कि रुकावट Wi‑Fi है या प्रोवाइडर।"),
    ("बफरब्लोट क्या है?", "जब कनेक्शन व्यस्त होता है (जैसे बड़े डाउनलोड के समय) तो पिंग बढ़ जाता है — इसी को बफरब्लोट कहते हैं। इसी वजह से किसी के बैकअप शुरू करते ही वीडियो कॉल अटक जाती है। हम लाइन लोड करके पिंग मापते हैं और बढ़ोतरी को ग्रेड देते हैं: A मतलब लगभग कोई बदलाव नहीं, F मतलब सैकड़ों मिलीसेकंड। SQM या \"Smart Queue\" वाले राउटर इसे ठीक करते हैं।"),
    ("अलग-अलग स्पीड टेस्ट अलग नंबर क्यों देते हैं?", "हर टेस्ट अलग सर्वर, अलग संख्या में कनेक्शन और अलग औसत तरीका इस्तेमाल करता है। सिंगल-कनेक्शन टेस्ट तेज़ प्लान पर कम दिखाते हैं। VPN और iCloud Private Relay उस ब्राउज़र के हर टेस्ट को सीमित करते हैं। एक नंबर की जगह कुछ बार टेस्ट करके ट्रेंड देखें।"),
    ("पिंग और जिटर का क्या मतलब है?", "पिंग सर्वर तक आने-जाने का समय है। 20 ms से कम बेहतरीन, 50 ms से कम गेमिंग के लिए शानदार, और 100 ms+ धीमा लगता है। जिटर बताता है कि पिंग कितना बदलता है; कम जिटर से कॉल और गेम स्मूद रहते हैं।"),
    ("यह टेस्ट कितना सटीक है?", "यह Cloudflare के नज़दीकी डेटा सेंटर (भारत में मुंबई, दिल्ली, चेन्नई, बेंगलुरु, हैदराबाद, कोलकाता आदि) से आठ तक समानांतर कनेक्शन खोलता है, शुरुआती दो सेकंड छोड़ता है और स्थिर स्पीड का औसत लेता है। यही तरीका Ookla जैसे टेस्ट इस्तेमाल करते हैं और यह गीगाबिट प्लान पर भी सही पढ़ता है।"),
 ],
}

# ----------------------------------------------------------------------------- Pages
# Each page: lang, slug ('' = home for that lang), nav, title, desc, h1, intro, faqs, plan (preset), mode ('test'|'outage'), alt (en slug for hreflang)
P = []
def page(lang, slug, nav, title, desc, h1, intro, faqs, plan=0, mode="test", alt=None):
    P.append(dict(lang=lang, slug=slug, nav=nav, title=title, desc=desc, h1=h1, intro=intro, faqs=faqs, plan=plan, mode=mode, alt=alt))

NOT_AFFIL = "No. gbps.run is independent and ad-free, and is not affiliated with any provider."

page("en", "", "Speed test", "gbps.run – Free Internet Speed Test (Download, Upload, Ping, Bufferbloat)",
     "Free, ad-free internet speed test. Measures download, upload, ping, jitter and bufferbloat, then tells you in plain English whether your connection handles 4K streaming, gaming, video calls and working from home.",
     "Internet speed test", "Download, upload, ping, jitter and bufferbloat in about 25 seconds — then plain-English verdicts on what your connection can actually handle. No ads, no sign-up.", GENERIC_FAQ["en"])
page("en", "wifi-speed-test", "Wi‑Fi", "Wi‑Fi Speed Test – How Fast Is Your Wi‑Fi Really? | gbps.run",
     "Test your Wi‑Fi speed from any phone or laptop. See download, upload, ping and bufferbloat, compare it with your plan, and learn why Wi‑Fi is slower than wired.",
     "Wi‑Fi speed test", "Run this on your phone or laptop over Wi‑Fi, then once more next to the router. The gap between the two is what your walls, distance and router are costing you.",
     [("Why is Wi‑Fi slower than my plan?", "Every wall and metre of distance costs signal; 2.4 GHz is slow and crowded; older routers and devices cap the link. Expect 50–90% of your plan near the router and far less in distant rooms."),
      ("How do I get faster Wi‑Fi?", "Put the router up high and in the open, use the 5 GHz or 6 GHz band for nearby devices, turn on 160 MHz channels on Wi‑Fi 6/6E/7 routers, update firmware, and add a wired access point or mesh node for far rooms."),
      ("Should I test wired too?", "Yes. If an Ethernet test is near your plan speed and Wi‑Fi is far below, the fix is on your side (router, placement, band). If wired is also slow, contact your provider."),
      ("What Wi‑Fi speed do I need?", "25 Mbps per 4K stream, 5–10 Mbps per video call, under 50 ms ping for gaming. Most homes are comfortable with 100–300 Mbps actually delivered over Wi‑Fi.")])
page("en", "xfinity-speed-test", "Xfinity", "Xfinity Speed Test – Are You Getting the Speed You Pay For? | gbps.run",
     "Independent speed test for Xfinity (Comcast) internet. Check download, upload, ping and bufferbloat, enter your plan and see the percentage you're actually getting.",
     "Xfinity speed test", "An independent test for Xfinity customers. Enter your plan speed after the test to see exactly what percentage you're getting — and whether the shortfall is Wi‑Fi or the line.",
     [("What speeds should I get on Xfinity?", "Xfinity cable plans typically range from about 150 Mbps to 2 Gbps download depending on your area, with upload speeds that are much lower on most tiers (often 10–35 Mbps, higher in upgraded markets). Gigabit plans are commonly provisioned slightly above 1,000 Mbps, so a wired test near 940 Mbps is normal."),
      ("Why is my Xfinity upload so slow?", "Cable networks dedicate far more capacity to download than upload. That's by design, not a fault. If upload matters for you (video calls, backups, streaming), check whether an upgraded tier or fibre is available at your address."),
      ("My Xfinity speed is low — what do I check first?", "Run a wired test. If it's also low, restart the modem, check the coax connections, and test at a quiet time. If it stays low, ask Xfinity to check signal levels. If wired is fine but Wi‑Fi is slow, the fix is the router or its placement."),
      ("Is this the official Xfinity speed test?", "No. gbps.run is independent and not affiliated with Comcast. It tests to Cloudflare's nearest server, which is a fair representation of real-world internet performance rather than a test inside the provider's own network.")])
page("en", "spectrum-speed-test", "Spectrum", "Spectrum Speed Test – Check Your Real Download & Upload Speed | gbps.run",
     "Independent speed test for Spectrum internet. Measure download, upload, ping and bufferbloat and compare with your 300 Mbps, 500 Mbps or Gig plan.",
     "Spectrum speed test", "Independent test for Spectrum customers. Spectrum plans are usually 300 Mbps, 500 Mbps or 1 Gig — enter yours after the test to see what you're really getting.",
     [("What speed should Spectrum deliver?", "Spectrum's main tiers are around 300, 500 and 1,000 Mbps download. Upload is typically 10–35 Mbps on cable, with higher uploads in markets that have been upgraded. Wired tests at 85–95% of the plan are normal; Wi‑Fi will be lower."),
      ("Why is Spectrum slow in the evening?", "Cable is shared with your neighbourhood, so 7–11 pm can be congested. Use monitor mode on this page to log speeds across a day; if evenings are consistently far lower, that's useful evidence when you contact Spectrum."),
      ("Should I use Spectrum's router?", "The provided router is fine for basic use but often lacks Wi‑Fi 6/6E/7 and good bufferbloat handling. Many customers get better Wi‑Fi from their own router in bridge mode."),
      ("Is this affiliated with Spectrum?", NOT_AFFIL)])
page("en", "att-speed-test", "AT&T", "AT&T Speed Test – Fiber & Internet Air | gbps.run",
     "Independent speed test for AT&T Fiber and AT&T Internet. Check symmetrical fibre speeds, ping and bufferbloat and compare with your plan.",
     "AT&T speed test", "For AT&T Fiber and AT&T Internet customers. Fibre plans are symmetrical, so your upload should be close to your download — this test shows both.",
     [("What should AT&T Fiber speeds look like?", "AT&T Fiber tiers are symmetrical (for example 300, 500, 1,000, 2,000 and 5,000 Mbps), so upload should roughly match download. A 1 Gig plan tests around 900–940 Mbps wired; multi-gig plans need a 2.5 Gbps or faster port to show more than ~940 Mbps."),
      ("Why does my AT&T gigabit test show only 940 Mbps?", "A standard gigabit Ethernet port tops out at about 940 Mbps of usable throughput. That's the cable, not AT&T. Over Wi‑Fi, 600–900 Mbps is a good result."),
      ("AT&T Internet Air is slow — is that normal?", "Internet Air is fixed wireless (5G), so speeds vary with signal and congestion, commonly 75–225 Mbps. Try moving the gateway near a window facing the tower."),
      ("Is this the official AT&T test?", NOT_AFFIL)])
page("en", "verizon-fios-speed-test", "Verizon Fios", "Verizon Fios Speed Test – Check Your Fibre Speed | gbps.run",
     "Independent speed test for Verizon Fios and Verizon 5G Home. Measure symmetrical download and upload, ping, jitter and bufferbloat.",
     "Verizon Fios speed test", "Fios is symmetrical fibre, so upload should be close to download. If it isn't, something between the ONT and your device is the limit.",
     [("What speeds should Fios give me?", "Fios tiers are symmetrical, commonly 300, 500, 1 Gig and 2 Gig. Wired gigabit tests at about 900–940 Mbps are normal. The 2 Gig plan needs a multi-gig port to show more."),
      ("My Fios upload is lower than download — why?", "Fios should be symmetrical. If upload is far lower, test wired; Wi‑Fi uplink is often weaker than downlink on phones. If wired upload is also low, check the router and contact Verizon."),
      ("Is Verizon 5G Home slower than Fios?", "Usually yes. 5G Home speeds vary with signal and congestion, often 85–300 Mbps and higher in strong Ultra Wideband areas. Ping is also higher than fibre."),
      ("Is this affiliated with Verizon?", NOT_AFFIL)])
page("en", "t-mobile-home-internet-speed-test", "T‑Mobile Home", "T‑Mobile Home Internet Speed Test – 5G Gateway Check | gbps.run",
     "Speed test for T‑Mobile 5G Home Internet. See download, upload, ping and bufferbloat, and learn how gateway placement changes your speed.",
     "T‑Mobile Home Internet speed test", "5G home internet lives and dies by signal. Run this test, move the gateway to a different window, and run it again — the difference can be huge.",
     [("What speeds are normal on T‑Mobile Home Internet?", "T‑Mobile quotes typical download speeds roughly in the 87–415 Mbps range and uploads of about 14–56 Mbps, depending on signal and network load. Ping is typically higher than cable or fibre."),
      ("How do I make it faster?", "Placement is everything: high up, near a window, facing the nearest tower, away from metal and thick walls. The T‑Mobile app shows signal bars; a 5G signal on the n41 band gives the best speeds."),
      ("Why does the speed change through the day?", "It's shared cellular capacity, so evenings in busy areas slow down. Use monitor mode on this page to log a full day."),
      ("Is this affiliated with T‑Mobile?", NOT_AFFIL)])
page("en", "starlink-speed-test", "Starlink", "Starlink Speed Test – Satellite Download, Upload & Latency | gbps.run",
     "Independent speed test for Starlink. Check download, upload, ping, jitter and bufferbloat, and see what's normal for satellite internet.",
     "Starlink speed test", "Satellite speed swings with weather, obstructions and how busy your cell is. Run a few tests at different times — and watch the ping and jitter, not just the download number.",
     [("What Starlink speeds are normal?", "Residential Starlink commonly delivers roughly 50–250 Mbps download, 10–25 Mbps upload and 25–60 ms ping, varying by region, time of day and plan. Brief drops are normal as satellites hand off."),
      ("Why is my Starlink slow right now?", "Common causes: obstructions (check the app's obstruction map), heavy rain or snow, a congested cell at peak hours, or Wi‑Fi limits inside the house. Test wired to the router to rule out Wi‑Fi."),
      ("Is Starlink good for gaming and calls?", "Usually fine for calls; gaming is playable but ping of 30–60 ms with occasional spikes isn't competitive-grade. Jitter and bufferbloat grades on this page tell you more than download speed."),
      ("Is this affiliated with Starlink or SpaceX?", NOT_AFFIL)])
page("en", "google-fiber-speed-test", "Google Fiber", "Google Fiber Speed Test – 1 Gig to 8 Gig | gbps.run",
     "Speed test for Google Fiber customers. Check symmetrical gigabit speeds, ping and bufferbloat, and learn why multi-gig plans need multi-gig hardware.",
     "Google Fiber speed test", "Google Fiber plans are symmetrical from 1 Gig up to 8 Gig. Over a standard gigabit port or Wi‑Fi you'll see up to ~940 Mbps; the faster tiers need 2.5G/10G hardware to show their full speed.",
     [("What should a Google Fiber test show?", "1 Gig wired: about 900–940 Mbps both ways. 2, 5 and 8 Gig: only as fast as your Ethernet port, Wi‑Fi and the browser allow — expect 900–2,300 Mbps on typical home gear."),
      ("Why doesn't my test show 2 Gbps?", "A gigabit Ethernet port caps at ~940 Mbps. You need a 2.5 Gbps port, a Wi‑Fi 6E/7 router with 160/320 MHz channels, and a recent device. Browsers also cap out around 2–3 Gbps."),
      ("Is this the Google Fiber official test?", NOT_AFFIL)])
page("en", "cox-speed-test", "Cox", "Cox Speed Test – Check Your Real Internet Speed | gbps.run",
     "Independent speed test for Cox internet. Measure download, upload, ping and bufferbloat and compare against your Cox plan.",
     "Cox speed test", "Independent test for Cox customers. Enter your plan after the test to see the percentage delivered, and check the bufferbloat grade if calls or games stutter.",
     [("What speeds should Cox deliver?", "Cox tiers typically run from about 100 Mbps to 2 Gbps download, with uploads of roughly 5–100 Mbps depending on tier and market. Wired tests at 85–95% of plan are normal."),
      ("Why is Cox upload so low?", "Cable upload capacity is limited by design. If you need more, check whether an upgraded tier or fibre is available."),
      ("Is this affiliated with Cox?", NOT_AFFIL)])
page("en", "quantum-fiber-speed-test", "Quantum Fiber", "Quantum Fiber Speed Test (CenturyLink Fiber) | gbps.run",
     "Speed test for Quantum Fiber and CenturyLink customers. Check symmetrical fibre speeds, ping, jitter and bufferbloat.",
     "Quantum Fiber speed test", "Quantum Fiber (formerly CenturyLink Fiber) is symmetrical. Upload should be close to download — if it isn't, the limit is on your side of the ONT.",
     [("What speeds should Quantum Fiber show?", "Common tiers are around 500 Mbps and 940 Mbps symmetrical, with multi-gig tiers in some areas. A 940 Mbps plan tests at about 900–940 Mbps wired."),
      ("Can I use my own router with Quantum Fiber?", "Yes. Most Quantum Fiber installs hand off plain Ethernet from the ONT, so your own router works. Some older CenturyLink lines need VLAN 201 tagging."),
      ("Is this affiliated with Quantum Fiber or Lumen?", NOT_AFFIL)])
page("en", "bufferbloat-test", "Bufferbloat", "Bufferbloat Test – Does Your Connection Lag When It's Busy? | gbps.run",
     "Free bufferbloat test. Measures ping while your connection is loaded and grades it A+ to F. Find out why video calls freeze and games lag even on fast plans.",
     "Bufferbloat test", "Fast download speed doesn't stop lag. Bufferbloat is the ping spike that happens when someone in the house downloads something — and it ruins calls and games. This test loads your line and measures exactly that.",
     [("What is bufferbloat?", "When your connection is saturated, routers and modems queue packets instead of dropping them, so everything waits in line. Ping that's 15 ms when idle can hit 300 ms+ under load. That's bufferbloat."),
      ("How is the grade calculated?", "We measure idle ping, then keep pinging during the download and upload phases. The increase is graded: A+ under 5 ms, A under 30, B under 60, C under 200, D under 400, F above that."),
      ("How do I fix bufferbloat?", "Turn on SQM, Smart Queue Management, fq_codel or CAKE on your router (OpenWrt, many ASUS, Ubiquiti, Firewalla, eero and others have it). Set the limits to ~90% of your real speeds. Grades typically jump from D/F to A."),
      ("Does a faster plan fix it?", "Not by itself. Bufferbloat is a queue-management problem, so a 1 Gbps plan can grade F while a well-managed 100 Mbps line grades A.")])
page("en", "ping-test", "Ping", "Ping Test – Check Latency & Jitter for Gaming | gbps.run",
     "Free ping test for gamers. Measures latency, jitter, packet loss and ping under load (bufferbloat) in your browser — no app needed.",
     "Ping test for gaming", "For gaming, ping and jitter matter more than download speed. This test measures idle ping, jitter, packet loss and — the one most tests miss — ping while the line is busy.",
     [("What is a good ping for gaming?", "Under 20 ms is excellent, 20–50 ms is great, 50–100 ms is playable, over 100 ms is noticeable. Jitter under 10 ms keeps movement smooth."),
      ("Why does my game lag when someone else is streaming?", "That's bufferbloat — ping spikes under load. Check the bufferbloat grade; if it's C or worse, enable SQM/QoS on your router."),
      ("Why is Wi‑Fi ping higher than Ethernet?", "Wi‑Fi adds a few milliseconds and, more importantly, jitter from interference and retransmits. Serious gaming is best on a cable."),
      ("Is this ping to the game server?", "No — it's to the nearest Cloudflare data centre, which is a good proxy for your connection's baseline. Game servers add distance on top.")])
page("en", "upload-speed-test", "Upload", "Upload Speed Test – Video Calls, Streaming & Backups | gbps.run",
     "Test your upload speed accurately. Multi-stream upload test with ping-under-load grading, plus what upload speed you need for Zoom, Twitch and cloud backups.",
     "Upload speed test", "Upload is the number providers don't advertise and the one that decides whether your video looks sharp on calls and how long backups take. This test measures it properly, with several parallel streams.",
     [("What upload speed do I need?", "Video calls: 3–5 Mbps per call for HD. Streaming to Twitch/YouTube: 6–10 Mbps for 1080p. Cloud backups and photo libraries: the more the better — 20 Mbps uploads 5 GB in about 35 minutes; 200 Mbps does it in under 4."),
      ("Why is my upload so much lower than download?", "Cable and many 5G home services are asymmetric by design. Fibre plans are symmetrical. If upload matters to you, that's the main reason to switch to fibre."),
      ("Why does upload read low on Wi‑Fi?", "Phones and laptops transmit with less power than the router, so uplink is often the weaker direction over Wi‑Fi. Test wired for the true number.")])
page("en", "zoom-speed-test", "Video calls", "Zoom & Teams Speed Test – Is Your Internet Good Enough for Video Calls? | gbps.run",
     "Check whether your connection can handle Zoom, Teams, Google Meet and FaceTime. Tests upload, ping, jitter and bufferbloat — the four things that make calls freeze.",
     "Video call readiness test", "Calls don't freeze because of download speed. They freeze because of upload, jitter and ping spikes when the line is busy. This test checks all four and gives you a straight answer.",
     [("What internet speed does Zoom need?", "Zoom recommends about 3–4 Mbps up and down for HD group calls; Teams and Meet are similar. Almost any plan has that. What breaks calls is jitter over ~30 ms, packet loss, and bufferbloat when someone else downloads."),
      ("Why does my video freeze while audio continues?", "Video is dropped first when bandwidth or ping degrades. Check the jitter and bufferbloat grade; if they're poor, move closer to the router, use Ethernet, or enable QoS/SQM."),
      ("Should I use Ethernet for important calls?", "Yes. A cable removes Wi‑Fi jitter and is the single biggest reliability upgrade for work-from-home calls.")])
page("en", "gaming-speed-test", "Gaming", "Gaming Speed Test – Ping, Jitter & Lag Check for PS5, Xbox, PC | gbps.run",
     "Is your internet good enough for online gaming? Test ping, jitter, packet loss, bufferbloat and download speed for PS5, Xbox, Switch and PC.",
     "Gaming internet test", "Lag isn't about download speed. It's ping, jitter, packet loss and what happens to your ping when someone else in the house starts a download. This test grades all of it.",
     [("What internet speed do I need for gaming?", "Most online games use under 1 Mbps. What you need is low ping (under 50 ms), low jitter (under 15 ms), zero packet loss and a bufferbloat grade of B or better. Download speed only matters for installing games."),
      ("Why do I lag when my speed test is fast?", "Bufferbloat: your ping spikes under load. Enable SQM or QoS on your router and put your console on Ethernet."),
      ("Is 5G home internet okay for gaming?", "Playable, but ping and jitter are higher and less stable than cable or fibre. Competitive players should prefer wired broadband.")])
page("en", "4k-streaming-speed-test", "4K streaming", "4K Streaming Speed Test – Netflix, YouTube, Disney+ | gbps.run",
     "Check if your internet can stream 4K without buffering. See how many simultaneous 4K streams your connection supports.",
     "4K streaming speed test", "4K needs about 25 Mbps per stream, steady. This test shows your real download speed and consistency and tells you how many 4K streams your home can run at once.",
     [("How much speed does 4K need?", "Netflix recommends 15 Mbps for 4K, YouTube about 20 Mbps, and 25 Mbps is a safe figure that covers high-bitrate content. Multiply by the number of TVs streaming at once."),
      ("Why does Netflix buffer when my speed is fine?", "Consistency matters more than peak speed. If the consistency score here is low, Wi‑Fi interference or congestion is likely. Try 5 GHz, move the router, or wire the TV."),
      ("Does the TV's Wi‑Fi matter?", "Yes — many TVs have slow 2.4 GHz-only Wi‑Fi. A cheap Ethernet cable to the TV or a streaming stick on 5 GHz fixes most buffering.")])
page("en", "ethernet-vs-wifi-speed-test", "Wired vs Wi‑Fi", "Ethernet vs Wi‑Fi Speed Test – Find Where Your Speed Goes | gbps.run",
     "Run the test on Wi‑Fi, then on Ethernet, and see exactly how much speed your Wi‑Fi is losing. History on this page keeps both results side by side.",
     "Ethernet vs Wi‑Fi speed test", "Run this twice: once on Wi‑Fi, once with a cable. Your history below keeps both. If wired is near your plan and Wi‑Fi isn't, the fix is your router or its placement — not your provider.",
     [("How much faster is Ethernet?", "On a gigabit plan a cable gives ~940 Mbps with ~1 ms added latency; good Wi‑Fi 6/6E/7 gives 600–900 Mbps nearby and far less through walls, plus more jitter."),
      ("My laptop has no Ethernet port — what now?", "A USB‑C to 2.5 GbE adapter costs about $20–30 and gives you the true wired number."),
      ("Wired is slow too — now what?", "Try another cable (Cat 5e or better) and port, restart modem then router, and test at a quiet time. If still low, the provider needs to look at the line.")])
page("en", "5g-speed-test", "5G / mobile", "5G Speed Test – Mobile Data Speed on iPhone & Android | gbps.run",
     "Test your 5G or LTE speed in the browser, no app required. See download, upload, ping and jitter on your phone's cellular connection.",
     "5G mobile speed test", "Turn off Wi‑Fi, then run the test to measure your phone's 5G or LTE connection. No app, no permissions, nothing installed.",
     [("What 5G speeds are normal?", "Low-band 5G is often 50–150 Mbps; mid-band (such as T‑Mobile Ultra Capacity or Verizon Ultra Wideband) commonly delivers 300–1,000+ Mbps. Upload is usually 10–50 Mbps."),
      ("How much data does this test use?", "Typically 100–400 MB on a fast connection; the test adapts to your speed. Use the Quick setting in Settings if you're on a limited plan."),
      ("Why is my 5G ping higher than home internet?", "Cellular adds 20–40 ms by nature. It's fine for most uses but not ideal for competitive gaming.")])
page("en", "gigabit-speed-test", "Gigabit", "Gigabit Speed Test – Is Your 1 Gbps Plan Delivering? | gbps.run",
     "Accurate speed test for gigabit and multi-gig plans. Multi-stream testing that reads correctly at 1 Gbps+, with plan comparison and the hardware limits explained.",
     "Gigabit speed test", "Most tests read low on gigabit plans. This one opens up to eight parallel streams and ignores ramp-up, so it reads correctly at 1 Gbps and beyond. Your plan is pre-set to 1,000 Mbps below.",
     [("Why does my gigabit plan test at 940 Mbps?", "That's the usable ceiling of a gigabit Ethernet port after protocol overhead. It means your plan is delivering fully. Providers often provision 1.1–1.2 Gbps so that single-port users still see ~940."),
      ("What Wi‑Fi do I need for gigabit?", "A Wi‑Fi 6, 6E or 7 router with 160 MHz channels enabled, and a device that supports them (most 2021+ phones and laptops). Expect 700–900+ Mbps in the same room."),
      ("How do I test above 1 Gbps?", "A 2.5 GbE or 10 GbE port, a multi-gig router port, and a recent computer. Browsers cap around 2–3 Gbps; beyond that use a command-line tool like iperf3.")], plan=1000)
page("en", "private-relay-speed-test", "Private Relay", "Why Is My Speed Test Slow in Safari? iCloud Private Relay Explained | gbps.run",
     "Speed tests in Safari capped at 200–300 Mbps and ping over 50 ms? iCloud Private Relay is the cause. This test detects it and shows how to measure your real speed.",
     "Safari speed test with iCloud Private Relay", "If every speed test in Safari tops out around 200–300 Mbps while your phone or Chrome gets far more, iCloud Private Relay is routing your traffic through Apple's relay. This test detects it automatically.",
     [("What is iCloud Private Relay?", "A privacy feature in iCloud+ that sends Safari traffic through two relays (Apple's and a partner's such as Cloudflare) so no one party sees both who you are and what you visit. It applies to Safari and some system traffic on iPhone, iPad and Mac."),
      ("Why does it make speed tests slow?", "Relay servers add distance and have their own capacity limits, so throughput is commonly capped in the low hundreds of Mbps and ping rises by 20–50 ms. Every speed test in Safari is affected the same way."),
      ("How do I measure my real speed?", "Turn it off temporarily: System Settings (or Settings on iPhone) → your name → iCloud → Private Relay → off. Or run the test in Chrome, Firefox or Edge, which don't use it. Turn it back on afterwards if you value the privacy.")])

# Outage pages (en)
OUT_FAQ = lambda isp, status: [
    (f"How do I know if {isp} is down or it's just me?", f"Check whether other devices in your home are also offline. If everything is down, restart the modem (unplug 30 seconds) and the router. If it's still down, check {isp}'s status page or app — it usually shows known outages in your area — and look at outage-tracking sites to see if neighbours are reporting the same."),
    (f"What should I do during a {isp} outage?", "Use your phone's hotspot for anything urgent, keep the modem powered on so it reconnects automatically, and note the start time — many providers credit you for extended outages if you ask."),
    ("The check above says I'm online but things are slow", "Run the full speed test. Low download, high ping under load or packet loss points at congestion or Wi‑Fi problems rather than an outage. The verdicts tell you what's affected."),
    (f"Is this affiliated with {isp}?", NOT_AFFIL),
]
for slug, isp, st in [("is-xfinity-down", "Xfinity", "xfinity.com/support/status"), ("is-spectrum-down", "Spectrum", "spectrum.net/outage"), ("is-att-down", "AT&T", "att.com/outages"),
                      ("is-verizon-down", "Verizon", "verizon.com/support/outage"), ("is-starlink-down", "Starlink", "starlink.com (app)"), ("is-cox-down", "Cox", "cox.com/outage"),
                      ("is-t-mobile-home-internet-down", "T‑Mobile Home Internet", "T‑Mobile Internet app"), ("is-google-fiber-down", "Google Fiber", "fiber.google.com/status")]:
    page("en", slug, f"Is {isp} down?", f"Is {isp} Down Right Now? Live Connection Check | gbps.run",
         f"Check in seconds whether {isp} is down for you or everyone. Live connectivity test, then a full speed test to see whether it's an outage, congestion or Wi‑Fi.",
         f"Is {isp} down right now?", f"This page checks your connection automatically. Then run the full test to tell an outage from slow Wi‑Fi. Official status: {st}.",
         OUT_FAQ(isp, st), mode="outage")

# Spanish
page("es", "", "Test de velocidad", "gbps.run – Test de velocidad de internet gratis (descarga, subida, ping, bufferbloat)",
     "Test de velocidad de internet gratis y sin anuncios. Mide descarga, subida, ping, jitter y bufferbloat y te dice en lenguaje claro si tu conexión sirve para 4K, juegos, videollamadas y teletrabajo.",
     "Test de velocidad de internet", "Descarga, subida, ping, jitter y bufferbloat en unos 25 segundos — y después, veredictos claros sobre lo que tu conexión puede hacer de verdad. Sin anuncios, sin registro.", GENERIC_FAQ["es"], alt="")
page("es", "test-velocidad-wifi", "Wi‑Fi", "Test de velocidad Wi‑Fi – ¿Qué tan rápido es tu Wi‑Fi en realidad? | gbps.run",
     "Mide la velocidad de tu Wi‑Fi desde el móvil o el portátil. Descarga, subida, ping y bufferbloat, comparación con tu plan y por qué el Wi‑Fi es más lento que el cable.",
     "Test de velocidad Wi‑Fi", "Haz la prueba desde tu móvil o portátil por Wi‑Fi y luego otra vez junto al router. La diferencia es lo que te cuestan las paredes, la distancia y el router.",
     [("¿Por qué el Wi‑Fi es más lento que mi plan?", "Cada pared y cada metro restan señal; la banda de 2,4 GHz es lenta y está saturada; los routers y dispositivos antiguos limitan el enlace. Espera un 50–90% de tu plan junto al router y bastante menos en habitaciones lejanas."),
      ("¿Cómo consigo un Wi‑Fi más rápido?", "Coloca el router en alto y despejado, usa la banda de 5 GHz o 6 GHz para los dispositivos cercanos, activa canales de 160 MHz en routers Wi‑Fi 6/6E/7, actualiza el firmware y añade un punto de acceso por cable o un nodo mesh para las habitaciones lejanas."),
      ("¿Debería probar también por cable?", "Sí. Si la prueba por Ethernet se acerca a tu plan y el Wi‑Fi queda muy por debajo, la solución está en tu casa (router, ubicación, banda). Si por cable también es lento, contacta con tu operador.")], alt="wifi-speed-test")
page("es", "test-de-ping", "Ping", "Test de ping – Latencia y jitter para juegos online | gbps.run",
     "Test de ping gratis para gamers. Mide latencia, jitter, pérdida de paquetes y ping con carga (bufferbloat) desde el navegador, sin instalar nada.",
     "Test de ping para juegos", "Para jugar, el ping y el jitter importan más que la velocidad de descarga. Este test mide el ping en reposo, el jitter, la pérdida de paquetes y — lo que casi ningún test mide — el ping cuando la línea está ocupada.",
     [("¿Qué ping es bueno para jugar?", "Menos de 20 ms es excelente, 20–50 ms muy bueno, 50–100 ms jugable y más de 100 ms se nota. Un jitter por debajo de 10 ms mantiene el movimiento fluido."),
      ("¿Por qué tengo lag cuando alguien ve una serie?", "Eso es bufferbloat: el ping se dispara cuando hay tráfico. Mira la calificación de bufferbloat; si es C o peor, activa SQM/QoS en tu router."),
      ("¿Es este el ping al servidor del juego?", "No, es al centro de datos de Cloudflare más cercano, una buena referencia de tu conexión. Los servidores del juego añaden distancia.")], alt="ping-test")
page("es", "test-bufferbloat", "Bufferbloat", "Test de bufferbloat – ¿Tu conexión tiene lag cuando hay tráfico? | gbps.run",
     "Test de bufferbloat gratis. Mide el ping con la conexión cargada y lo califica de A+ a F. Descubre por qué las videollamadas se congelan y los juegos van con lag aunque tengas mucha velocidad.",
     "Test de bufferbloat", "Tener mucha descarga no evita el lag. El bufferbloat es el pico de ping que aparece cuando alguien en casa descarga algo, y arruina llamadas y partidas. Este test carga tu línea y mide exactamente eso.",
     [("¿Qué es el bufferbloat?", "Cuando la conexión se satura, routers y módems encolan paquetes en lugar de descartarlos, y todo espera en la fila. Un ping de 15 ms en reposo puede superar 300 ms con carga."),
      ("¿Cómo se calcula la nota?", "Medimos el ping en reposo y seguimos midiéndolo durante la descarga y la subida. El aumento se califica: A+ menos de 5 ms, A menos de 30, B menos de 60, C menos de 200, D menos de 400, F por encima."),
      ("¿Cómo se arregla?", "Activa SQM, Smart Queue Management, fq_codel o CAKE en el router (OpenWrt, muchos ASUS, Ubiquiti, Firewalla, eero…). Ajusta los límites a ~90% de tu velocidad real. La nota suele pasar de D/F a A.")], alt="bufferbloat-test")
page("es", "test-velocidad-subida", "Subida", "Test de velocidad de subida – Videollamadas, streaming y copias | gbps.run",
     "Mide tu velocidad de subida con precisión, con varias conexiones en paralelo y calificación de ping con carga. Qué subida necesitas para Zoom, Twitch y copias en la nube.",
     "Test de velocidad de subida", "La subida es el número que los operadores no anuncian y el que decide si tu vídeo se ve nítido en las llamadas y cuánto tardan las copias. Este test la mide bien, con varias conexiones en paralelo.",
     [("¿Qué velocidad de subida necesito?", "Videollamadas: 3–5 Mbps por llamada en HD. Streaming en Twitch/YouTube: 6–10 Mbps para 1080p. Copias en la nube: cuanto más mejor — con 20 Mbps, 5 GB tardan unos 35 minutos; con 200 Mbps, menos de 4."),
      ("¿Por qué mi subida es mucho menor que la descarga?", "El cable y muchos servicios 5G son asimétricos por diseño. La fibra es simétrica. Si la subida te importa, es la razón principal para pasarte a fibra.")], alt="upload-speed-test")

# Portuguese (pt-BR)
page("pt", "", "Teste de velocidade", "gbps.run – Teste de velocidade de internet grátis (download, upload, ping, bufferbloat)",
     "Teste de velocidade de internet grátis e sem anúncios. Mede download, upload, ping, jitter e bufferbloat e diz em linguagem clara se sua conexão serve para 4K, jogos, videochamadas e home office.",
     "Teste de velocidade de internet", "Download, upload, ping, jitter e bufferbloat em cerca de 25 segundos — depois, veredictos claros sobre o que sua conexão realmente aguenta. Sem anúncios, sem cadastro.", GENERIC_FAQ["pt"], alt="")
page("pt", "teste-velocidade-wifi", "Wi‑Fi", "Teste de velocidade Wi‑Fi – Quão rápido é seu Wi‑Fi de verdade? | gbps.run",
     "Meça a velocidade do seu Wi‑Fi pelo celular ou notebook. Download, upload, ping e bufferbloat, comparação com seu plano e por que o Wi‑Fi é mais lento que o cabo.",
     "Teste de velocidade Wi‑Fi", "Faça o teste no celular ou notebook pelo Wi‑Fi e depois de novo ao lado do roteador. A diferença é o que paredes, distância e roteador estão custando.",
     [("Por que o Wi‑Fi é mais lento que meu plano?", "Cada parede e cada metro tiram sinal; a banda de 2,4 GHz é lenta e lotada; roteadores e aparelhos antigos limitam o link. Espere 50–90% do plano perto do roteador e bem menos em cômodos distantes."),
      ("Como ter um Wi‑Fi mais rápido?", "Coloque o roteador no alto e sem obstáculos, use a banda de 5 GHz ou 6 GHz para aparelhos próximos, ative canais de 160 MHz em roteadores Wi‑Fi 6/6E/7, atualize o firmware e adicione um ponto de acesso cabeado ou mesh para cômodos distantes."),
      ("Devo testar no cabo também?", "Sim. Se o teste no cabo chega perto do plano e o Wi‑Fi fica bem abaixo, a solução está na sua casa (roteador, posição, banda). Se no cabo também é lento, fale com a operadora.")], alt="wifi-speed-test")
page("pt", "teste-de-ping", "Ping", "Teste de ping – Latência e jitter para jogos online | gbps.run",
     "Teste de ping grátis para gamers. Mede latência, jitter, perda de pacotes e ping sob carga (bufferbloat) no navegador, sem instalar nada.",
     "Teste de ping para jogos", "Para jogar, ping e jitter importam mais que a velocidade de download. Este teste mede o ping em repouso, o jitter, a perda de pacotes e — o que quase nenhum teste mede — o ping com a linha ocupada.",
     [("Qual ping é bom para jogar?", "Abaixo de 20 ms é excelente, 20–50 ms muito bom, 50–100 ms jogável e acima de 100 ms já se nota. Jitter abaixo de 10 ms mantém o movimento fluido."),
      ("Por que dá lag quando alguém assiste streaming?", "Isso é bufferbloat: o ping dispara com tráfego. Veja a nota de bufferbloat; se for C ou pior, ative SQM/QoS no roteador."),
      ("Este é o ping até o servidor do jogo?", "Não, é até o data center da Cloudflare mais próximo, uma boa referência da sua conexão. Os servidores do jogo adicionam distância.")], alt="ping-test")
page("pt", "teste-bufferbloat", "Bufferbloat", "Teste de bufferbloat – Sua conexão trava quando há tráfego? | gbps.run",
     "Teste de bufferbloat grátis. Mede o ping com a conexão carregada e dá nota de A+ a F. Descubra por que videochamadas congelam e jogos dão lag mesmo com muita velocidade.",
     "Teste de bufferbloat", "Muito download não evita lag. Bufferbloat é o pico de ping que aparece quando alguém em casa baixa algo — e arruína chamadas e partidas. Este teste carrega sua linha e mede exatamente isso.",
     [("O que é bufferbloat?", "Quando a conexão satura, roteadores e modems enfileiram pacotes em vez de descartá-los, e tudo espera na fila. Um ping de 15 ms em repouso pode passar de 300 ms sob carga."),
      ("Como a nota é calculada?", "Medimos o ping em repouso e continuamos medindo durante o download e o upload. O aumento recebe nota: A+ abaixo de 5 ms, A abaixo de 30, B abaixo de 60, C abaixo de 200, D abaixo de 400, F acima disso."),
      ("Como corrigir?", "Ative SQM, Smart Queue Management, fq_codel ou CAKE no roteador (OpenWrt, muitos ASUS, Ubiquiti, Firewalla, eero…). Ajuste os limites para ~90% da velocidade real. A nota costuma subir de D/F para A.")], alt="bufferbloat-test")
page("pt", "teste-velocidade-upload", "Upload", "Teste de velocidade de upload – Videochamadas, streaming e backups | gbps.run",
     "Meça seu upload com precisão, com várias conexões em paralelo e nota de ping sob carga. Qual upload você precisa para Zoom, Twitch e backups na nuvem.",
     "Teste de velocidade de upload", "Upload é o número que as operadoras não anunciam e o que decide se seu vídeo fica nítido nas chamadas e quanto tempo os backups levam. Este teste mede direito, com várias conexões em paralelo.",
     [("Qual velocidade de upload eu preciso?", "Videochamadas: 3–5 Mbps por chamada em HD. Streaming na Twitch/YouTube: 6–10 Mbps para 1080p. Backups na nuvem: quanto mais melhor — com 20 Mbps, 5 GB levam uns 35 minutos; com 200 Mbps, menos de 4."),
      ("Por que meu upload é bem menor que o download?", "Cabo e muitos serviços 5G são assimétricos por design. Fibra é simétrica. Se o upload importa para você, esse é o principal motivo para mudar para fibra.")], alt="upload-speed-test")


# India (English queries dominate Indian search; Hindi pages for Hindi-first users)
page("en", "jio-speed-test", "Jio", "Jio Speed Test – JioFiber, AirFiber & Jio 5G | gbps.run",
     "Independent speed test for JioFiber, Jio AirFiber and Jio 5G. Check download, upload, ping, jitter and bufferbloat and compare with your 30, 100, 300 Mbps or 1 Gbps plan.",
     "Jio speed test", "For JioFiber, Jio AirFiber and Jio True 5G users. Enter your plan after the test to see the percentage delivered — and whether the gap is Wi‑Fi or the line.",
     [("What speeds should JioFiber deliver?", "JioFiber plans run from 30 Mbps up to 1 Gbps and are symmetrical on most tiers, so upload should be close to download. Wired tests at 85–95% of the plan are normal; Wi‑Fi over the Jio router is often lower in distant rooms."),
      ("Why is my Jio 5G speed test slow?", "5G speed depends on which band you're on and how busy the tower is. Jio True 5G on the n78 band commonly delivers 200–800 Mbps; the low-band n28 is much slower. Try near a window, and turn off Wi‑Fi before testing."),
      ("Jio AirFiber is slow in the evening — normal?", "AirFiber is fixed wireless on 5G, so it shares the tower with phones and slows at peak hours. Use monitor mode on this page to log a full day and see the pattern."),
      ("Is this the official Jio speed test?", NOT_AFFIL)])
page("en", "airtel-speed-test", "Airtel", "Airtel Speed Test – Xstream Fiber, Airtel 5G Plus | gbps.run",
     "Independent speed test for Airtel Xstream Fiber and Airtel 5G Plus. Download, upload, ping, jitter and bufferbloat, with your plan percentage.",
     "Airtel speed test", "For Airtel Xstream Fiber and Airtel 5G Plus users. Run the test, enter your plan and see what you're really getting.",
     [("What speeds should Airtel Xstream Fiber give?", "Xstream Fiber plans are typically 40, 100, 200, 300 Mbps and 1 Gbps, usually symmetrical. A wired test at 85–95% of the plan is normal; the 1 Gbps plan shows ~900–940 Mbps on a gigabit port."),
      ("Why is my Airtel 5G Plus speed test low?", "Airtel 5G Plus uses the n78 band for high speed; if your phone falls back to 4G or low-band 5G the speed drops sharply. Test with Wi‑Fi off, near a window, and compare times of day."),
      ("Is this the official Airtel speed test?", NOT_AFFIL)])

page("hi", "", "स्पीड टेस्ट", "gbps.run – मुफ़्त इंटरनेट स्पीड टेस्ट (डाउनलोड, अपलोड, पिंग, बफरब्लोट)",
     "मुफ़्त, बिना विज्ञापन वाला इंटरनेट स्पीड टेस्ट। डाउनलोड, अपलोड, पिंग, जिटर और बफरब्लोट मापता है और साफ़ भाषा में बताता है कि आपका कनेक्शन 4K, गेमिंग, वीडियो कॉल और वर्क फ्रॉम होम के लिए ठीक है या नहीं।",
     "इंटरनेट स्पीड टेस्ट", "लगभग 25 सेकंड में डाउनलोड, अपलोड, पिंग, जिटर और बफरब्लोट — फिर साफ़ भाषा में बताया जाएगा कि आपका कनेक्शन असल में क्या-क्या संभाल सकता है। कोई विज्ञापन नहीं, कोई साइन-अप नहीं।", GENERIC_FAQ["hi"], alt="")
page("hi", "wifi-speed-test", "Wi‑Fi", "Wi‑Fi स्पीड टेस्ट – आपका Wi‑Fi असल में कितना तेज़ है? | gbps.run",
     "फ़ोन या लैपटॉप से अपने Wi‑Fi की स्पीड जाँचें। डाउनलोड, अपलोड, पिंग और बफरब्लोट, प्लान से तुलना, और Wi‑Fi केबल से धीमा क्यों होता है।",
     "Wi‑Fi स्पीड टेस्ट", "पहले अपने फ़ोन या लैपटॉप से Wi‑Fi पर टेस्ट करें, फिर राउटर के पास जाकर दोबारा। दोनों का अंतर ही वह स्पीड है जो दीवारें, दूरी और राउटर खा रहे हैं।",
     [("Wi‑Fi मेरे प्लान से धीमा क्यों है?", "हर दीवार और हर मीटर दूरी सिग्नल घटाती है; 2.4 GHz धीमा और भीड़ वाला है; पुराने राउटर और डिवाइस लिंक सीमित करते हैं। राउटर के पास प्लान का 50–90% और दूर के कमरों में उससे बहुत कम मिलना सामान्य है।"),
      ("Wi‑Fi तेज़ कैसे करें?", "राउटर ऊँचाई पर और खुली जगह रखें, पास के डिवाइस 5 GHz या 6 GHz बैंड पर रखें, Wi‑Fi 6/6E/7 राउटर में 160 MHz चैनल चालू करें, फ़र्मवेयर अपडेट करें, और दूर के कमरों के लिए LAN से जुड़ा एक्सेस पॉइंट या मेश नोड लगाएँ।"),
      ("क्या LAN केबल से भी टेस्ट करूँ?", "हाँ। अगर केबल पर स्पीड प्लान के पास है और Wi‑Fi बहुत कम, तो समस्या आपके घर में है (राउटर, जगह, बैंड)। अगर केबल पर भी कम है, तो प्रोवाइडर से बात करें।")], alt="wifi-speed-test")
page("hi", "ping-test", "पिंग", "पिंग टेस्ट – गेमिंग के लिए लेटेंसी और जिटर (BGMI, Free Fire) | gbps.run",
     "गेमर्स के लिए मुफ़्त पिंग टेस्ट। ब्राउज़र में ही लेटेंसी, जिटर, पैकेट लॉस और लोड के साथ पिंग (बफरब्लोट) मापें — कोई ऐप नहीं।",
     "गेमिंग के लिए पिंग टेस्ट", "गेमिंग में डाउनलोड स्पीड से ज़्यादा पिंग और जिटर मायने रखते हैं। यह टेस्ट आराम का पिंग, जिटर, पैकेट लॉस और — जो ज़्यादातर टेस्ट नहीं मापते — लाइन व्यस्त होने पर पिंग मापता है।",
     [("गेमिंग के लिए अच्छा पिंग कितना है?", "20 ms से कम बेहतरीन, 20–50 ms शानदार, 50–100 ms खेलने लायक, 100 ms से ऊपर साफ़ महसूस होता है। 10 ms से कम जिटर मूवमेंट स्मूद रखता है।"),
      ("जब कोई और स्ट्रीम करता है तो मेरा गेम लैग क्यों करता है?", "यही बफरब्लोट है — ट्रैफ़िक में पिंग उछलता है। बफरब्लोट ग्रेड देखें; C या उससे खराब हो तो राउटर में SQM/QoS चालू करें।"),
      ("क्या यह गेम सर्वर तक का पिंग है?", "नहीं — यह नज़दीकी Cloudflare डेटा सेंटर तक है, जो आपके कनेक्शन की बेसलाइन का अच्छा अंदाज़ा है। गेम सर्वर इसके ऊपर दूरी जोड़ते हैं।")], alt="ping-test")
page("hi", "bufferbloat-test", "बफरब्लोट", "बफरब्लोट टेस्ट – ट्रैफ़िक के समय क्या आपका कनेक्शन लैग करता है? | gbps.run",
     "मुफ़्त बफरब्लोट टेस्ट। लोड के साथ पिंग मापकर A+ से F तक ग्रेड देता है। जानें कि तेज़ प्लान पर भी वीडियो कॉल क्यों अटकती हैं और गेम लैग क्यों करते हैं।",
     "बफरब्लोट टेस्ट", "तेज़ डाउनलोड स्पीड लैग नहीं रोकती। बफरब्लोट वह पिंग-उछाल है जो घर में कोई कुछ डाउनलोड करे तो आता है — और यह कॉल और गेम बिगाड़ देता है। यह टेस्ट आपकी लाइन लोड करके ठीक यही मापता है।",
     [("बफरब्लोट क्या है?", "जब कनेक्शन भर जाता है, राउटर और मॉडम पैकेट गिराने के बजाय कतार में लगा देते हैं, और सब कुछ इंतज़ार करता है। आराम में 15 ms का पिंग लोड में 300 ms+ हो सकता है।"),
      ("ग्रेड कैसे तय होता है?", "हम आराम का पिंग मापते हैं, फिर डाउनलोड और अपलोड के दौरान भी पिंग मापते रहते हैं। बढ़ोतरी का ग्रेड: A+ 5 ms से कम, A 30 से कम, B 60 से कम, C 200 से कम, D 400 से कम, F उससे ऊपर।"),
      ("इसे कैसे ठीक करें?", "राउटर में SQM, Smart Queue Management, fq_codel या CAKE चालू करें (OpenWrt, कई ASUS, Ubiquiti, Firewalla, eero आदि में होता है)। लिमिट असली स्पीड के ~90% पर रखें। ग्रेड आमतौर पर D/F से A हो जाता है।")], alt="bufferbloat-test")
page("hi", "jio-speed-test", "Jio", "Jio स्पीड टेस्ट – JioFiber, AirFiber और Jio 5G | gbps.run",
     "JioFiber, Jio AirFiber और Jio 5G के लिए स्वतंत्र स्पीड टेस्ट। डाउनलोड, अपलोड, पिंग, जिटर और बफरब्लोट जाँचें और अपने प्लान से तुलना करें।",
     "Jio स्पीड टेस्ट", "JioFiber, Jio AirFiber और Jio True 5G यूज़र्स के लिए। टेस्ट के बाद अपना प्लान डालें और देखें कि कितना प्रतिशत मिल रहा है — और कमी Wi‑Fi की है या लाइन की।",
     [("JioFiber में कितनी स्पीड मिलनी चाहिए?", "JioFiber प्लान 30 Mbps से 1 Gbps तक हैं और ज़्यादातर में अपलोड-डाउनलोड बराबर होते हैं। LAN केबल पर प्लान का 85–95% सामान्य है; Jio राउटर के Wi‑Fi पर दूर के कमरों में कम मिलना आम है।"),
      ("मेरा Jio 5G स्पीड टेस्ट धीमा क्यों है?", "5G स्पीड इस पर निर्भर है कि आप किस बैंड पर हैं और टावर कितना व्यस्त है। n78 बैंड पर Jio True 5G आमतौर पर 200–800 Mbps देता है; n28 लो-बैंड बहुत धीमा है। खिड़की के पास और Wi‑Fi बंद करके टेस्ट करें।"),
      ("क्या यह Jio का आधिकारिक टेस्ट है?", "नहीं। gbps.run स्वतंत्र है, बिना विज्ञापन का है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="jio-speed-test")
page("hi", "airtel-speed-test", "Airtel", "Airtel स्पीड टेस्ट – Xstream Fiber और Airtel 5G Plus | gbps.run",
     "Airtel Xstream Fiber और Airtel 5G Plus के लिए स्वतंत्र स्पीड टेस्ट। डाउनलोड, अपलोड, पिंग, जिटर और बफरब्लोट, आपके प्लान के प्रतिशत के साथ।",
     "Airtel स्पीड टेस्ट", "Airtel Xstream Fiber और Airtel 5G Plus यूज़र्स के लिए। टेस्ट करें, अपना प्लान डालें और देखें कि असल में क्या मिल रहा है।",
     [("Airtel Xstream Fiber में कितनी स्पीड मिलनी चाहिए?", "Xstream Fiber प्लान आमतौर पर 40, 100, 200, 300 Mbps और 1 Gbps के होते हैं, ज़्यादातर सिमेट्रिकल। LAN पर प्लान का 85–95% सामान्य है; 1 Gbps प्लान गीगाबिट पोर्ट पर ~900–940 Mbps दिखाता है।"),
      ("मेरा Airtel 5G Plus टेस्ट कम क्यों है?", "Airtel 5G Plus तेज़ स्पीड के लिए n78 बैंड इस्तेमाल करता है; फ़ोन 4G या लो-बैंड 5G पर चला जाए तो स्पीड तेज़ी से गिरती है। Wi‑Fi बंद करके, खिड़की के पास, और दिन के अलग समय पर टेस्ट करें।"),
      ("क्या यह Airtel का आधिकारिक टेस्ट है?", "नहीं। gbps.run स्वतंत्र है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="airtel-speed-test")

# ----------------------------------------------------------------------------- Rendering helpers
def url_of(p):
    base = ROOT if p["lang"] == "en" else f"{ROOT}/{p['lang']}"
    return f"{base}/{p['slug']}/" if p["slug"] else f"{base}/"
def path_of(p):
    base = "" if p["lang"] == "en" else f"/{p['lang']}"
    return f"{base}/{p['slug']}/" if p["slug"] else f"{base}/"

BY_LANG = {}
for p in P: BY_LANG.setdefault(p["lang"], []).append(p)
EN_BY_SLUG = {p["slug"]: p for p in BY_LANG["en"]}

def nav_for(lang):
    return "".join(f'<a href="{path_of(p)}">{html.escape(p["nav"])}</a>' for p in BY_LANG[lang]) + '<a href="https://gbps.live/">Live monitor ↗</a>'

def hreflang_for(p):
    # group: an en page and its translations (alt points at the en slug)
    en_slug = p["slug"] if p["lang"] == "en" else p["alt"]
    if en_slug is None: return ""
    group = [q for q in P if (q["lang"] == "en" and q["slug"] == en_slug) or (q["lang"] != "en" and q["alt"] == en_slug)]
    if len(group) < 2: return ""
    tags = [f'<link rel="alternate" hreflang="{q["lang"] if q["lang"] != "pt" else "pt-BR"}" href="{url_of(q)}">' for q in group]
    en = next(q for q in group if q["lang"] == "en"); tags.append(f'<link rel="alternate" hreflang="x-default" href="{url_of(en)}">')
    return "\n".join(tags)

def lang_switch(p):
    en_slug = p["slug"] if p["lang"] == "en" else p["alt"]
    group = [q for q in P if (q["lang"] == "en" and q["slug"] == en_slug) or (q["lang"] != "en" and q["alt"] == en_slug)] if en_slug is not None else []
    others = [q for q in group if q["lang"] != p["lang"]]
    if not others: others = [q for q in P if q["slug"] == "" and q["lang"] != p["lang"]]
    return " ".join(f'<a class="iconbtn lang" href="{path_of(q)}" hreflang="{q["lang"]}">{LANG_NAMES[q["lang"]]}</a>' for q in others)

OUTAGE_EXTRA = '<div id="outageStatus" class="status" role="status" aria-live="polite">…</div>'
LIVE_EXTRA = '<div id="liveBox" class="status" role="status" aria-live="polite">…</div>'

def render(p, embed=False):
    S = STR[p["lang"]]; url = url_of(p); out = TEMPLATE
    subs = {
        "{{LANG}}": p["lang"], "{{OG_LOCALE}}": OG_LOCALE[p["lang"]], "{{TITLE}}": html.escape(p["title"]), "{{TITLE_JSON}}": json.dumps(p["title"], ensure_ascii=False),
        "{{DESC}}": html.escape(p["desc"]), "{{URL}}": url, "{{HREFLANG}}": hreflang_for(p), "{{HOME}}": "/" if p["lang"] == "en" else f"/{p['lang']}/",
        "{{LANG_SWITCH}}": lang_switch(p), "{{H1}}": p["h1"], "{{INTRO}}": p["intro"], "{{EXTRA}}": OUTAGE_EXTRA if p["mode"] == "outage" else (LIVE_EXTRA if p["mode"] == "live" else ""),
        "{{FAQ_HEADING}}": {"en": "Understanding your results", "es": "Entiende tus resultados", "pt": "Entenda seus resultados", "hi": "अपने रिज़ल्ट समझें"}[p["lang"]] if not p["slug"] else {"en": "Questions about this test", "es": "Preguntas sobre este test", "pt": "Perguntas sobre este teste", "hi": "इस टेस्ट के बारे में सवाल"}[p["lang"]],
        "{{FAQ_HTML}}": faq_html(p["faqs"]), "{{FAQ_JSON}}": faq_json(p["faqs"]), "{{NAV}}": nav_for(p["lang"]),
        "{{PLAN_PRESET}}": str(p["plan"] or 0), "{{MODE}}": p["mode"], "{{L_JSON}}": json.dumps(S, ensure_ascii=False), "{{ANALYTICS}}": ANALYTICS,
    }
    for k, v in subs.items(): out = out.replace(k, v)
    out = re.sub(r"\{\{t:(\w+)\}\}", lambda m: html.escape(str(S[m.group(1)])), out)
    assert "{{" not in out, [l for l in out.split("\n") if "{{" in l][:3]
    if embed:
        out = out.replace("</style>", "#faq,#more,#embed,#historyCard,header .row,footer{display:none !important}.wrap{padding:8px}</style>")
        out = out.replace('<meta name="robots" content="index,follow,max-image-preview:large">', '<meta name="robots" content="noindex">')
    return out

STATIC_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="{desc}"><link rel="canonical" href="{url}"><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%230b0f17'/%3E%3Cpath d='M14 40a20 20 0 0 1 36 0' stroke='%233ee6a5' stroke-width='6' fill='none' stroke-linecap='round'/%3E%3Cpath d='M32 40 44 24' stroke='%23fff' stroke-width='5' stroke-linecap='round'/%3E%3C/svg%3E"><style>body{{font-family:Inter,system-ui,sans-serif;background:#0b0f17;color:#e8edf5;margin:0;line-height:1.6}}main{{max-width:720px;margin:0 auto;padding:24px 16px 60px}}a{{color:#5aa9ff}}h1{{letter-spacing:-.02em}}.btn{{display:inline-block;background:#3ee6a5;color:#06130d;font-weight:800;padding:12px 24px;border-radius:999px;text-decoration:none;margin-top:12px}}p,li{{color:#b8c2d3}}</style></head><body><main><a href="/" style="font-weight:800;color:#e8edf5;text-decoration:none">gbps.run</a>{body}</main></body></html>"""
ABOUT = """<h1>About gbps.run</h1><p>gbps.run is a free, ad-free internet speed test built to answer the question people actually have: <em>is my internet good enough for what I do?</em></p><p>It measures download, upload, ping, jitter and packet loss, and — unlike most tests — ping <strong>under load</strong>, which is graded as bufferbloat. It then gives plain-English verdicts for 4K streaming, video calls, gaming, working from home and more. It also detects when a VPN or iCloud Private Relay is distorting your results.</p><ul><li>Runs entirely in your browser; nothing to install.</li><li>Test data is exchanged with Cloudflare's nearest data centre, which has hundreds of locations worldwide.</li><li>No ads, no accounts, no tracking. Results are stored only on your own device.</li><li>Free to embed on any website. Available in English, Spanish and Portuguese.</li></ul><p>gbps.run is independent and not affiliated with any internet provider.</p><a class="btn" href="/">Run the test</a>"""
PRIVACY = """<h1>Privacy</h1><p>gbps.run does not use advertising, tracking cookies or user accounts.</p><ul><li><strong>Test traffic:</strong> the test downloads and uploads random bytes to Cloudflare's speed-test endpoints (speed.cloudflare.com); if those are unreachable, a public CDN file is used for the download portion. Those services see your IP address as part of serving that traffic, as any website does.</li><li><strong>Connection info:</strong> your IP, network name and nearest server are fetched from Cloudflare to display on the page. They're shown to you only and not stored by gbps.run.</li><li><strong>History:</strong> your past results are saved in your browser's local storage on your device. Clear them any time with the Clear history button.</li><li><strong>Shared result links:</strong> contain only the numbers you choose to share, in the link itself. Nothing is stored on a server.</li><li><strong>Analytics:</strong> if enabled, the site uses privacy-friendly, cookie-free page-view counting only.</li></ul><a class="btn" href="/">Back to the test</a>"""
NOT_FOUND = """<h1>Page not found</h1><p>That page doesn't exist — but the speed test does.</p><a class="btn" href="/">Run a speed test</a>"""

def og_image(path):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (11, 15, 23)); d = ImageDraw.Draw(im)
    def font(sz, bold=True):
        for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]:
            if os.path.exists(f): return ImageFont.truetype(f, sz)
        return ImageFont.load_default()
    d.arc([760, 120, 1120, 480], 180, 360, fill=(36, 48, 65), width=28); d.arc([760, 120, 1120, 480], 180, 330, fill=(62, 230, 165), width=28)
    d.text((940, 300), "940", fill=(232, 237, 245), font=font(96), anchor="mm"); d.text((940, 365), "Mbps", fill=(141, 154, 176), font=font(28, False), anchor="mm")
    d.text((80, 150), "gbps.run", fill=(62, 230, 165), font=font(72)); d.text((80, 250), "Free internet speed test", fill=(232, 237, 245), font=font(44))
    for i, line in enumerate(["Download · Upload · Ping · Jitter", "Bufferbloat grade (A+ to F)", "Plain-English verdicts: 4K, Zoom, gaming", "No ads · No sign-up · 25 seconds"]):
        d.text((80, 330 + i * 52), "•  " + line, fill=(184, 194, 211), font=font(28, False))
    im.save(path, optimize=True)

HTACCESS = """# gbps.run – Hostinger/Apache config
RewriteEngine On
# Any other hostname (www, hostingersite.com preview, etc.) and plain http → the canonical domain
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} !^gbps[.]run$ [NC]
RewriteRule ^ https://gbps.run%{REQUEST_URI} [L,R=301]
ErrorDocument 404 /404.html
# Source files live in _src/ (git) – never serve them
RedirectMatch 404 ^/_src(/|$)
RedirectMatch 404 ^/[.]git(/|$)
RedirectMatch 404 ^/README[.]md$
<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css application/javascript application/json image/svg+xml text/xml
</IfModule>
<IfModule mod_headers.c>
<FilesMatch "[.](html)$">
Header set Cache-Control "public, max-age=600"
</FilesMatch>
<FilesMatch "[.](png|svg|ico|webp)$">
Header set Cache-Control "public, max-age=2592000"
</FilesMatch>
Header set X-Content-Type-Options "nosniff"
Header set Referrer-Policy "strict-origin-when-cross-origin"
Header set Permissions-Policy "camera=(), microphone=(), geolocation=()"
</IfModule>
"""


# ----------------------------------------------------------------------------- gbps.live (separate site: live connection monitor)
LIVE_ROOT = "https://gbps.live"
LIVE_PAGE = dict(lang="en", slug="", nav="Live monitor", mode="live", plan=0, alt=None,
    title="gbps.live – Live Internet Monitor: Is My Internet Dropping?",
    desc="Leave this tab open and gbps.live tests your connection every 5 minutes, charts the day, and logs every drop — download, upload, ping and bufferbloat over time. Free, no account.",
    h1="Live internet monitor",
    intro="Leave this tab open. Your connection is tested every 5 minutes and every drop is logged, so when the internet \"feels slow in the evening\" you have the chart to prove it. One-off test? Use <a href='https://gbps.run/'>gbps.run</a>.",
    faqs=[("How does the live monitor work?", "It runs a quick 6-second test (ping, download, upload) at the interval you choose while the tab is open, keeps the results on your device, and summarises uptime, drops and the speed range for the last 24 hours. Nothing is sent to a server."),
          ("What counts as a drop?", "A check that fails entirely, or whose download speed is below half of your typical speed for the day. Both show in the table so you can see when they happened."),
          ("Does it work when the laptop is asleep or the tab is in the background?", "Browsers pause background tabs, so keep it in a visible window (a second monitor or a spare phone on the charger works well). Checks skip while the tab is hidden rather than recording false drops."),
          ("Can I use this as evidence with my provider?", "Yes — Copy as CSV exports every check with timestamps. A day of logged evening slowdowns or repeated drops is far more persuasive than one bad speed test."),
          ("How much data does it use?", "Roughly 20–60 MB per check on a fast connection, so about 300 MB–1 GB per hour at 5-minute intervals. Use a longer interval on metered connections.")])

LIVE_HTACCESS = """RewriteEngine On
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} !^gbps[.]live$ [NC]
RewriteRule ^ https://gbps.live%{REQUEST_URI} [L,R=301]
# Only the monitor lives here; everything else is on gbps.run
RewriteCond %{REQUEST_URI} !^/(index\\.html)?$
RewriteCond %{REQUEST_URI} !^/(og[.]png|robots[.]txt|sitemap[.]xml)$
RewriteRule ^(.*)$ https://gbps.run/$1 [L,R=301]
<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css application/javascript application/json image/svg+xml text/xml
</IfModule>
<IfModule mod_headers.c>
Header set X-Content-Type-Options "nosniff"
Header set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>
"""

def build_live(out="site-live"):
    if os.path.exists(out): shutil.rmtree(out)
    os.makedirs(out)
    html_out = render(LIVE_PAGE)
    html_out = html_out.replace(f'href="{ROOT}/"', 'href="https://gbps.live/"').replace('content="https://gbps.run/"', 'content="https://gbps.live/"')
    html_out = html_out.replace('<link rel="canonical" href="https://gbps.run/">', '<link rel="canonical" href="https://gbps.live/">')
    html_out = html_out.replace('"url":"https://gbps.run/","inLanguage"', '"url":"https://gbps.live/","inLanguage"')
    html_out = html_out.replace('"name":"gbps.run Internet Speed Test","url":"https://gbps.run/"', '"name":"gbps.live Live Internet Monitor","url":"https://gbps.live/"')
    html_out = html_out.replace('class="logo" href="/"', 'class="logo" href="https://gbps.live/"').replace('href="/"', 'href="https://gbps.run/"').replace('href="/', 'href="https://gbps.run/')
    html_out = html_out.replace('<a href="https://gbps.live/">Live monitor ↗</a>', '')
    html_out = html_out.replace('>gbps.run\n    </a>', '>gbps.live\n    </a>').replace("      gbps.run\n    </a>", "      gbps.live\n    </a>")
    html_out = html_out.replace('<footer>gbps.run ·', '<footer>gbps.live · a <a href="https://gbps.run/">gbps.run</a> tool ·')
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html_out)
    open(os.path.join(out, ".htaccess"), "w").write(LIVE_HTACCESS)
    today = datetime.date.today().isoformat()
    open(os.path.join(out, "sitemap.xml"), "w").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>{LIVE_ROOT}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>\n</urlset>\n')
    open(os.path.join(out, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {LIVE_ROOT}/sitemap.xml\n")
    shutil.copy(os.path.join(OUT, "og.png"), os.path.join(out, "og.png"))
    print(f"built gbps.live → {out}/")

def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT); urls = []
    for p in P:
        d = os.path.join(OUT, path_of(p).strip("/")); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(render(p))
        urls.append((url_of(p), "1.0" if not p["slug"] else ("0.8" if p["mode"] == "test" else "0.7")))
    os.makedirs(os.path.join(OUT, "embed"), exist_ok=True)
    home = EN_BY_SLUG[""]; emb = dict(home); emb.update(title="gbps.run speed test (embed)", intro="Powered by <a href='https://gbps.run' target='_blank' rel='noopener'>gbps.run</a>")
    open(os.path.join(OUT, "embed", "index.html"), "w", encoding="utf-8").write(render(emb, embed=True))
    for slug, title, desc, body in [("about", "About gbps.run – free, independent speed test", "What gbps.run measures, how it works and why it's free.", ABOUT), ("privacy", "Privacy – gbps.run", "gbps.run privacy: no ads, no tracking, results stay on your device.", PRIVACY)]:
        os.makedirs(os.path.join(OUT, slug), exist_ok=True)
        open(os.path.join(OUT, slug, "index.html"), "w", encoding="utf-8").write(STATIC_PAGE.format(title=title, desc=desc, url=f"{ROOT}/{slug}/", body=body)); urls.append((f"{ROOT}/{slug}/", "0.3"))
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(STATIC_PAGE.format(title="Not found – gbps.run", desc="", url=f"{ROOT}/", body=NOT_FOUND))
    today = datetime.date.today().isoformat()
    open(os.path.join(OUT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod><priority>{pr}</priority></url>\n" for u, pr in urls) + "</urlset>\n")
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nDisallow: /embed/\nSitemap: {ROOT}/sitemap.xml\n")
    open(os.path.join(OUT, ".htaccess"), "w").write(HTACCESS)
    og_image(os.path.join(OUT, "og.png"))
    print(f"built {len(urls)} pages → {OUT}/")
    build_live()

if __name__ == "__main__":
    main()
