#!/usr/bin/env python3
"""Builds the gbps.run static site into ./site from template.html.
Run: python3 build.py  → copy site/* to the repo root (Hostinger deploys the repo root into public_html)."""
import json, os, re, shutil, html, datetime

ROOT = "https://gbps.run"
OUT = "site"
TEMPLATE = open("template.html", encoding="utf-8").read()
# Speed-test backends, tried in order by the page. The first is our own Worker (deploy from _src/worker/, see its README);
# the second is Cloudflare's shared endpoint, used automatically if ours is unreachable or over its free-tier quota.
BACKENDS = ["https://gbps-speed.parthaagrawal1.workers.dev", "https://speed.cloudflare.com"]
ANALYTICS = {
    "gbps.run": """<script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "0968f4ef414b4594b164ff29299ca51e"}'></script>""",
    "gbps.live": """<script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "8f2b49e14d4d460abb7c3d0258179561"}'></script>""",
}

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
    more_h="More tests", embed_h="Put this test on your site", embed_p="Free to embed. Paste this where you want the test to appear:", embed_credit="Speed test by", embed_badge="Or add a badge that links to the test:",
    footer="free · no ads, no tracking · results stay on your device", about="about", privacy="privacy",
    # JS
    ph_server="Finding the nearest server…", ph_ping="Measuring ping…", ph_down="Testing download…", ph_up="Testing upload…", ph_done="Done · {note} connection", ph_stopped="Test stopped", ph_failed="Test failed",
    err_offline="You appear to be offline. Check your connection and try again.",
    err_server="Could not reach the test servers. Check that you are online, then try again. (If this page is embedded in a sandbox or a strict corporate network, open it at its own address.)", err_limited="The test server is rate-limiting this connection right now, so no reliable measurement was possible. Wait a minute and try again.",
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
    fallback_server="fallback server", fallback_note="download-only fallback server used", limited_note="the test server was rate-limiting this connection, so the result may read low — try again in a minute",
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
    more_h="Más pruebas", embed_h="Pon esta prueba en tu web", embed_p="Gratis para insertar. Pega esto donde quieras que aparezca la prueba:", embed_credit="Test de velocidad de", embed_badge="O añade una insignia que enlace a la prueba:",
    footer="gratis · sin anuncios ni rastreo · los resultados se quedan en tu dispositivo", about="acerca de", privacy="privacidad",
    ph_server="Buscando el servidor más cercano…", ph_ping="Midiendo ping…", ph_down="Probando descarga…", ph_up="Probando subida…", ph_done="Listo · conexión {note}", ph_stopped="Prueba detenida", ph_failed="La prueba falló",
    err_offline="Parece que no tienes conexión. Revisa tu red e inténtalo de nuevo.",
    err_server="No se pudo conectar con los servidores de prueba. Comprueba que tienes internet e inténtalo de nuevo.", err_limited="El servidor de prueba está limitando esta conexión ahora mismo, así que no fue posible medir con fiabilidad. Espera un minuto e inténtalo de nuevo.",
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
    fallback_server="servidor alternativo", fallback_note="se usó un servidor alternativo (solo descarga)", limited_note="el servidor de prueba limitó esta conexión, así que el resultado puede ser bajo — inténtalo de nuevo en un minuto",
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
    more_h="Mais testes", embed_h="Coloque este teste no seu site", embed_p="Grátis para incorporar. Cole isto onde quiser que o teste apareça:", embed_credit="Teste de velocidade de", embed_badge="Ou adicione um selo que leve ao teste:",
    footer="grátis · sem anúncios nem rastreamento · os resultados ficam no seu dispositivo", about="sobre", privacy="privacidade",
    ph_server="Procurando o servidor mais próximo…", ph_ping="Medindo ping…", ph_down="Testando download…", ph_up="Testando upload…", ph_done="Pronto · conexão {note}", ph_stopped="Teste interrompido", ph_failed="O teste falhou",
    err_offline="Parece que você está offline. Verifique sua conexão e tente de novo.",
    err_server="Não foi possível alcançar os servidores de teste. Verifique se você está online e tente de novo.", err_limited="O servidor de teste está limitando esta conexão agora, então não foi possível medir com confiança. Espere um minuto e tente de novo.",
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
    fallback_server="servidor alternativo", fallback_note="servidor alternativo usado (só download)", limited_note="o servidor de teste limitou esta conexão, então o resultado pode estar baixo — tente de novo em um minuto",
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
    more_h="और टेस्ट", embed_h="यह टेस्ट अपनी वेबसाइट पर लगाएँ", embed_p="मुफ़्त में एम्बेड करें। जहाँ टेस्ट दिखाना हो वहाँ यह पेस्ट करें:", embed_credit="स्पीड टेस्ट:", embed_badge="या एक बैज जोड़ें जो टेस्ट से लिंक हो:",
    footer="मुफ़्त · कोई विज्ञापन या ट्रैकिंग नहीं · रिज़ल्ट आपके डिवाइस पर ही रहते हैं", about="परिचय", privacy="प्राइवेसी",
    ph_server="नज़दीकी सर्वर खोजा जा रहा है…", ph_ping="पिंग मापा जा रहा है…", ph_down="डाउनलोड टेस्ट हो रहा है…", ph_up="अपलोड टेस्ट हो रहा है…", ph_done="पूरा · {note} कनेक्शन", ph_stopped="टेस्ट रोका गया", ph_failed="टेस्ट फेल हो गया",
    err_offline="लगता है आप ऑफ़लाइन हैं। कनेक्शन जाँचें और फिर कोशिश करें।",
    err_server="टेस्ट सर्वर तक पहुँच नहीं हो पाई। जाँचें कि इंटरनेट चल रहा है और फिर कोशिश करें।", err_limited="टेस्ट सर्वर अभी इस कनेक्शन को सीमित कर रहा है, इसलिए भरोसेमंद माप नहीं हो पाया। एक मिनट रुककर फिर कोशिश करें।",
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
    fallback_server="वैकल्पिक सर्वर", fallback_note="वैकल्पिक सर्वर (सिर्फ़ डाउनलोड) इस्तेमाल हुआ", limited_note="टेस्ट सर्वर ने इस कनेक्शन को सीमित किया, इसलिए नतीजा कम दिख सकता है — एक मिनट बाद फिर कोशिश करें",
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

# US ISPs — batch 2
page("en", "frontier-fiber-speed-test", "Frontier Fiber", "Frontier Fiber Speed Test – Check Symmetrical Speeds | gbps.run",
     "Independent speed test for Frontier Fiber and Frontier DSL. Measure download, upload, ping and bufferbloat, then compare with your 500 Mbps, 1 Gig or 2 Gig tier.",
     "Frontier Fiber speed test", "Built for Frontier customers on fibre or legacy DSL. Run the test, enter your plan to see the percentage delivered, and look at upload — on Frontier Fiber it should be nearly identical to download.",
     [("What speeds should Frontier Fiber deliver?", "Frontier's fibre tiers commonly run from 200 Mbps to 2 Gbps, with 5 Gbps and 7 Gbps offered in some markets, and they're symmetrical: upload should land within a few percent of download. A wired test at 85–95% of plan is normal. On Frontier DSL, 10–115 Mbps download with a few Mbps upload is typical, so compare against the speed in your bill rather than the fibre figures."),
      ("Why does my Frontier Fiber test show less than a gigabit?", "Most often the test device is the cap. A laptop on Wi‑Fi 5 will top out around 400–600 Mbps, and a 1 GbE port can never read above ~940 Mbps. For the 2 Gig plan you need a 2.5 GbE port and a Wi‑Fi 6E/7 router. If a wired 2.5 GbE test still reads under 1 Gbps, check that the ONT-to-router cable is Cat 5e or better and that the router's WAN port is multi-gig."),
      ("My Frontier connection is fast but video calls still freeze", "Check the bufferbloat grade. Fibre lines rarely congest, but the supplied router can still queue traffic badly when someone uploads. A grade of C or worse points at the router; enabling SQM or a smart-queue setting, or swapping in a router that supports it, usually fixes it."),
      ("Is this affiliated with Frontier?", NOT_AFFIL)])
page("en", "centurylink-speed-test", "CenturyLink", "CenturyLink Speed Test – DSL and Fiber Check | gbps.run",
     "Independent speed test for CenturyLink internet. Check download, upload, ping and bufferbloat against your DSL or fibre plan and see where the limit is.",
     "CenturyLink speed test", "For CenturyLink DSL and fibre customers (fibre accounts are now sold as Quantum Fiber). Run the test, enter the speed on your bill, and compare the wired and Wi‑Fi results to see where the shortfall comes from.",
     [("What speeds should CenturyLink deliver?", "CenturyLink DSL is typically sold at 10, 20, 40, 80, 100 or 140 Mbps depending on how far you are from the equipment, with uploads commonly 1–20 Mbps. DSL is distance-sensitive, so a wired result at 80–90% of the advertised speed is normal and the connection should read the same at midnight as at 8 pm. Fibre plans run 200 Mbps to multi-gigabit and are symmetrical."),
      ("Why does my CenturyLink DSL drop speed in the evening?", "DSL itself doesn't slow with the time of day — the copper line gives a fixed sync rate. Evening drops usually mean congestion further back at CenturyLink's aggregation point, or Wi‑Fi interference from neighbours. Leave the monitor running for a day: a flat line that dips 7–11 pm is a complaint-worthy pattern; random dips at any hour point at Wi‑Fi or a noisy phone line."),
      ("How do I check if a bad phone line is slowing CenturyLink?", "Log in to the modem (often 192.168.0.1) and look for the DSL status page. SNR margin under about 6 dB, high CRC error counts, or frequent re-syncs mean the line is marginal. Unplug every other phone device, use a DSL filter, and try the modem on the first jack where the line enters the house."),
      ("Is this affiliated with CenturyLink or Lumen?", NOT_AFFIL)])
page("en", "optimum-speed-test", "Optimum", "Optimum Speed Test – Cable and Fiber Internet Check | gbps.run",
     "Independent speed test for Optimum internet. Measure download, upload, ping and bufferbloat, then compare with your 300, 500, 1 Gig or Optimum Fiber plan.",
     "Optimum speed test", "For Optimum customers in New York, New Jersey, Connecticut and the former Suddenlink markets. Run the test on Wi‑Fi and then on a cable; enter your plan to see the percentage delivered and whether upload is holding you back.",
     [("What speeds should Optimum deliver?", "Optimum's cable tiers commonly run 300 Mbps, 500 Mbps and 1 Gig download, with uploads typically 20–50 Mbps on cable. Optimum Fiber tiers are symmetrical, from 300 Mbps to 8 Gbps in some areas. Cable download at 85–100% of plan on a wired test is normal; some areas read slightly above plan because of built-in overprovisioning."),
      ("Why is my Optimum upload so low?", "Cable networks give far more capacity to download than upload, so 20–35 Mbps upload on a gigabit cable plan is typical and not a fault. If you upload large files or run several video calls at once, that's the figure that matters. Optimum Fiber, where available, removes the asymmetry entirely."),
      ("Optimum speed is fine but games lag and calls stutter", "Look at ping under load and the bufferbloat grade. Cable upload saturates easily — one person backing up photos can push ping from 15 ms to 300 ms for everyone. A D or F grade means the gateway isn't managing its queue; a router with SQM set to about 90% of your measured upload speed fixes it."),
      ("Is this affiliated with Optimum or Altice?", NOT_AFFIL)])
page("en", "mediacom-speed-test", "Mediacom", "Mediacom Speed Test – Xtream Cable Plan Check | gbps.run",
     "Independent speed test for Mediacom Xtream internet. Measure download, upload, ping and bufferbloat, then compare with your 100 Mbps, 300 Mbps or 1 Gig plan.",
     "Mediacom speed test", "For Mediacom Xtream customers across the Midwest and South. Run the test once on Wi‑Fi and once on a cable to the gateway, then enter your plan to see the percentage delivered and whether the gap is in your house or on the line.",
     [("What speeds should Mediacom deliver?", "Mediacom's Xtream tiers commonly run from 100 Mbps up to 1 Gig download, with uploads typically 10–50 Mbps on cable depending on the tier. Wired download at 85–100% of plan is normal, and Mediacom often provisions a little above the advertised figure. Over Wi‑Fi, 50–80% is typical on a gigabit plan because the supplied gateway's radio becomes the limit before the line does."),
      ("Why does Mediacom slow down in the evening in my town?", "Mediacom serves many smaller cities and rural areas where one cable node can cover a large neighbourhood, so 7–11 pm congestion shows up more clearly than in dense metros. Leave the monitor on this page running for a day: an afternoon reading near your plan and a nightly dip of 40% or more is node congestion, not your router, and the exported CSV is useful when you ask Mediacom to split the node."),
      ("Does Mediacom's data cap affect my speed?", "Mediacom plans have historically come with monthly data allowances, and some tiers slow or charge after the allowance is used — check your current plan terms. A sudden drop late in a billing month, with an otherwise healthy ping, is worth comparing against your usage meter in the Mediacom account before troubleshooting hardware."),
      ("Is this affiliated with Mediacom?", NOT_AFFIL)])
page("en", "wow-speed-test", "WOW!", "WOW! Internet Speed Test – Cable and Fiber Check | gbps.run",
     "Independent speed test for WOW! Internet (WideOpenWest). Check download, upload, ping and bufferbloat and compare with your 300 Mbps, 500 Mbps or 1 Gig plan.",
     "WOW! Internet speed test", "For WOW! customers in the Midwest and Southeast, on cable or the newer WOW! fibre builds. Run the test wired and on Wi‑Fi and enter your plan: cable tiers should read close to plan on download, and fibre tiers should show upload nearly matching download.",
     [("What speeds should WOW! deliver?", "WOW!'s cable tiers typically run 300, 500 and 1,000 Mbps download, with uploads commonly in the 20–50 Mbps range. In the newer all-fibre markets, plans are symmetrical and reach multi-gigabit. On cable, a wired test at 85–100% of plan is normal; on fibre, expect 900–940 Mbps on a 1 Gig plan because a standard Ethernet port caps there."),
      ("How can I tell whether my WOW! service is cable or fibre?", "Look at the box WOW! installed. A coax screw-on connector feeding a cable modem means cable (DOCSIS); a small white ONT with a thin fibre lead means fibre. The test tells you too: fibre upload will be close to download, while cable upload is a small fraction of it. Knowing which you have sets the right expectations for the numbers above."),
      ("WOW! download is fine but ping jumps during uploads", "That's bufferbloat and it is very common on cable gateways. When someone starts a cloud backup the limited upload fills up and ping can climb from 15 ms to several hundred. Check the grade on this page: C or worse means the gateway isn't managing its queue. Putting the gateway in bridge mode behind a router with SQM, limited to about 90% of your measured upload, usually turns an F into an A."),
      ("Is this affiliated with WOW! or WideOpenWest?", NOT_AFFIL)])
page("en", "astound-speed-test", "Astound", "Astound Speed Test – RCN, Grande & Wave Check | gbps.run",
     "Independent speed test for Astound Broadband (formerly RCN, Grande and Wave). Check download, upload, ping and bufferbloat against your 300 Mbps to 1.5 Gig plan.",
     "Astound Broadband speed test", "For Astound customers on the former RCN, Grande and Wave networks. Run the test wired and on Wi‑Fi, enter your plan, and check the upload figure — it tells you whether your address is on Astound's cable or fibre network.",
     [("What speeds should Astound deliver?", "Astound's cable tiers commonly run from 300 Mbps to 1.5 Gbps download, with uploads typically 15–50 Mbps. Where Astound has built fibre (parts of its Texas, Pacific Northwest and East Coast footprint), plans are symmetrical, so upload should match download. A wired cable test at 85–100% of plan is normal; a 1.5 Gig plan needs a 2.5 GbE port to read above about 940 Mbps."),
      ("I was an RCN, Grande or Wave customer — did anything change?", "The brand changed to Astound, but the physical network at your address is the same one those companies built, so expect the same behaviour: a legacy cable area still has asymmetric upload and some evening congestion, while a fibre area is symmetrical and flat through the day. The test result, not the brand name, tells you which you're on."),
      ("Astound speed is low — what do I check first?", "Reboot the modem and router (unplug 30 seconds each), then test on a cable straight from the modem. If that reads near plan, the shortfall is Wi‑Fi: use the 5 GHz band and move the router into the open. If wired is also low, test at midday and again at 9 pm with the monitor on this page — a steady low means a line or provisioning issue to raise with Astound; an evening-only drop means node congestion."),
      ("Is this affiliated with Astound, RCN, Grande or Wave?", NOT_AFFIL)])
page("en", "brightspeed-speed-test", "Brightspeed", "Brightspeed Speed Test – Fiber and DSL Plan Check | gbps.run",
     "Independent speed test for Brightspeed Fiber and Brightspeed DSL (former CenturyLink lines). Check download, upload, ping and bufferbloat against your plan.",
     "Brightspeed speed test", "For Brightspeed customers on the copper lines it took over from CenturyLink and on its newer fibre builds. Run the test, enter the speed on your bill, and look at the upload figure — it tells you straight away whether your address is on fibre or DSL.",
     [("What speeds should Brightspeed deliver?", "Brightspeed Fiber tiers commonly run from 300 Mbps to 1 Gbps and are symmetrical, so upload should sit within a few percent of download; a 1 Gig plan reads about 900–940 Mbps on a wired gigabit port. Brightspeed DSL is a different story: typical tiers are 20–140 Mbps download with 1–20 Mbps upload, and the sync rate depends on distance to the cabinet, so compare against the speed on your bill rather than the fibre figures."),
      ("My Brightspeed DSL reads well under the plan speed — is that normal?", "A wired result at 80–90% of the advertised DSL speed is normal because the line's sync rate includes overhead. A result at half or less points at a line problem: log in to the modem and look for low SNR margin (under about 6 dB), rising CRC errors or repeated re-syncs. Removing other phone devices, fitting a DSL filter and moving the modem to the first jack in the house often recovers 10–30 Mbps on marginal lines."),
      ("Brightspeed Fiber is fast but gets laggy when someone uploads", "That's bufferbloat in the supplied gateway, not the fibre. Watch the bufferbloat grade on this page: C or worse means the router queues traffic instead of managing it. Turning on SQM or a smart-queue option, or putting the gateway in bridge mode behind a router that has one, typically brings a D or F grade up to A within one test run."),
      ("Is this affiliated with Brightspeed?", NOT_AFFIL)])
page("en", "ziply-fiber-speed-test", "Ziply Fiber", "Ziply Fiber Speed Test – Gig, 2 Gig & 5 Gig Check | gbps.run",
     "Independent speed test for Ziply Fiber in Washington, Oregon, Idaho and Montana. Measure download, upload, ping and bufferbloat against your gig or multi-gig plan.",
     "Ziply Fiber speed test", "For Ziply Fiber customers in the Pacific Northwest, including those still on the former Frontier copper lines. Run the test wired and on Wi‑Fi and enter your plan — on Ziply's multi-gig tiers the device you test from is the limit far more often than the line.",
     [("What speeds should Ziply Fiber deliver?", "Ziply's fibre tiers commonly start around 100–300 Mbps and go to 1 Gig, 2 Gig, 5 Gig and in some areas 10 Gig and above, all symmetrical. A 1 Gig plan tests around 900–940 Mbps on a standard gigabit port; anything above that needs a 2.5 GbE or 10 GbE port and a browser test will top out near 2.5 Gbps regardless. Legacy Ziply DSL on the old Frontier copper is typically 10–115 Mbps with low upload."),
      ("Why does my 2 Gig or 5 Gig Ziply plan test below 1 Gbps?", "Almost always the test device. A laptop with a 1 GbE port can never read above ~940 Mbps, and even Wi‑Fi 6E tops out around 1–1.5 Gbps in practice. To see multi-gig speeds you need a 2.5 GbE or faster port, a Cat 6 cable to the ONT or router, and a router whose LAN and WAN ports are both multi-gig. If a 10 GbE wired test still reads under 1 Gbps, the Ziply ONT may be provisioned for the wrong tier — worth a call."),
      ("Ziply speed is lower in the evening — isn't fibre supposed to be flat?", "A passive optical network splits one fibre among a few dozen homes, so a small peak-hour dip is possible, but a 30–50% evening drop on a fibre plan is unusual. Run the monitor on this page through a full day: a flat line with a small 8–10 pm dip is normal; a large consistent dip, or one that also appears on a wired test, is evidence to send to Ziply."),
      ("Is this affiliated with Ziply Fiber?", NOT_AFFIL)])
page("en", "metronet-speed-test", "Metronet", "Metronet Speed Test – 100% Fiber Symmetrical Check | gbps.run",
     "Independent speed test for Metronet fibre internet. Check download, upload, ping and bufferbloat and compare with your 500 Mbps, 1 Gig, 2 Gig or 5 Gig plan.",
     "Metronet speed test", "For Metronet customers across the Midwest and South. Metronet is fibre to the home, so upload should match download — run the test wired and on Wi‑Fi, enter your plan, and the gap between the two runs shows how much the supplied Wi‑Fi is costing you.",
     [("What speeds should Metronet deliver?", "Metronet plans commonly run 500 Mbps, 1 Gig, 2 Gig and 5 Gig, with 100–200 Mbps entry tiers in some markets, and every tier is symmetrical. On a wired gigabit port a 1 Gig plan reads about 900–940 Mbps; the 2 Gig and 5 Gig plans need a 2.5 GbE or faster port to show more. Over the supplied Wi‑Fi, 400–800 Mbps on a 1 Gig plan is a typical good result."),
      ("Does Metronet's Wi‑Fi equipment limit my speed?", "Often, yes. Metronet supplies eero mesh units in many areas, and a single Wi‑Fi 6 eero in a cupboard will deliver far less than the line can. Put the unit in the open near the centre of the house, connect fixed devices to it by Ethernet, and if you have more than one eero, wire them together (Ethernet backhaul) instead of letting them mesh wirelessly. A wired test straight from the ONT or the first eero tells you what the line itself is doing."),
      ("Metronet ping is low but games still stutter — what's wrong?", "Check jitter and the bufferbloat grade rather than the average ping. Fibre gives a steady 5–20 ms idle ping in most Metronet cities, so if the loaded ping climbs to 100 ms or more, the router is queuing. Eero's optimised-for-gaming or QoS settings help; a router with SQM set to about 90% of your measured speeds fixes it outright. Packet loss above 1% on a wired test, on the other hand, is a line issue to report."),
      ("Is this affiliated with Metronet?", NOT_AFFIL)])

page("en", "kinetic-windstream-speed-test", "Kinetic", "Kinetic by Windstream Speed Test – Fiber & DSL Check | gbps.run",
     "Independent speed test for Kinetic by Windstream. Measure download, upload, ping and bufferbloat, then compare with your Kinetic Fiber or DSL plan.",
     "Kinetic by Windstream speed test", "For Kinetic customers in the rural and small-town markets Windstream serves. Run the test, enter the speed on your bill, and compare a wired result with Wi‑Fi — on Kinetic Fiber the two numbers should be close, on DSL the line itself is usually the cap.",
     [("What speeds should Kinetic deliver?", "Kinetic Fiber tiers commonly run from 300 Mbps to 1 Gig, with 2 Gig and faster offered in some towns, and they're symmetrical, so upload should sit within a few percent of download. Kinetic DSL (sold as Kinetic Internet without the word Fiber) is typically 25–100 Mbps download with 1–10 Mbps upload, and the exact rate depends on how far your home is from Windstream's cabinet. On a wired test, 85–95% of the advertised figure is normal for either."),
      ("My Kinetic DSL is far below the advertised speed — is that normal?", "Partly. DSL is sold as 'up to' because the copper line syncs at a rate set by distance and line quality, and that sync rate is your real ceiling. Log in to the modem and compare the DSL sync rate with your test: if the two match, the line is doing all it can and the only real fix is Kinetic Fiber if it has reached your street. If the test reads well under the sync rate, restart the modem, try a different phone jack and filter, and test wired — those three steps clear most cases."),
      ("Kinetic speeds drop every evening — who's at fault?", "On Kinetic Fiber, an evening dip usually isn't the line, which doesn't share bandwidth with neighbours the way cable does; check Wi‑Fi interference first and whether another device is backing up or streaming. On DSL, evening slowdowns typically come from congestion on Windstream's backhaul out of a small town rather than your copper pair. Leave monitor mode running for a day: a consistent 7–11 pm trough on a wired connection is the evidence to take to support."),
      ("Is this affiliated with Kinetic or Windstream?", NOT_AFFIL)])
page("en", "hughesnet-speed-test", "HughesNet", "HughesNet Speed Test – Satellite Speed & Latency Check | gbps.run",
     "Independent speed test for HughesNet satellite internet. Check download, upload, ping and jitter, see what's normal and learn why satellite ping is so high.",
     "HughesNet speed test", "HughesNet beams your traffic to a satellite about 35,000 km up and back, so ping is high by design — focus on whether download is in the expected range and whether it drops once you pass your data allowance. Run this test wired to the modem if you can, and again at a quiet hour for a fair baseline.",
     [("What HughesNet speeds are normal?", "HughesNet's current Jupiter 3 service is commonly sold at 50–100 Mbps download with about 5 Mbps upload, and older plans at around 25 Mbps. Real results typically land at 60–100% of the advertised figure outside peak hours and lower in the evening when the beam serving your area is busy. Ping of 600–800 ms is normal for geostationary satellite and not something a reboot will change."),
      ("Why is my HughesNet ping so high?", "Physics. The signal travels roughly 35,000 km to the satellite and back twice per round trip, which alone costs about 500 ms before any network delay is added. That makes fast-twitch online gaming, remote desktop and some VPNs frustrating, though email, streaming and web browsing work fine. If ping is what you need to fix, only a low-earth-orbit service like Starlink or a 5G home connection can bring it down."),
      ("HughesNet was fine, now it's suddenly slow — what happened?", "Check your data usage first. Most HughesNet plans drop to a much slower rate (often 1–3 Mbps) once you've used the month's priority data, which is the most common cause of a sudden slowdown mid-month. Otherwise, heavy rain or snow, a dish nudged out of alignment, or a growing tree in the line of sight will cut speed; the modem's status page shows signal quality, and a reading that's fallen over time points at alignment or obstructions."),
      ("Is this affiliated with HughesNet or EchoStar?", NOT_AFFIL)])
page("en", "viasat-speed-test", "Viasat", "Viasat Speed Test – Satellite Download, Upload & Ping | gbps.run",
     "Independent speed test for Viasat satellite internet. Measure download, upload, ping and jitter, and find out whether weather, data limits or Wi‑Fi is the cap.",
     "Viasat speed test", "Viasat is geostationary satellite, so expect high ping and a download number that varies with weather, time of day and your data usage. Test next to the Viasat router over Wi‑Fi, then on a cable if you can, and repeat at a quiet hour to see what the link can really do.",
     [("What speeds should Viasat deliver?", "Viasat's unlimited plans are commonly sold at 25–150 Mbps download depending on the satellite beam covering your address, with upload typically around 3–5 Mbps. In practice 50–90% of the advertised download outside peak hours is normal, and evenings often run lower because everyone in your beam shares the same capacity. Ping of 600 ms or more is expected on any geostationary service."),
      ("Why does Viasat slow down after I watch a lot of video?", "Viasat's plans have a monthly data threshold; once you cross it your traffic is deprioritised behind other customers whenever the beam is busy, so speeds can fall sharply at peak times even though nothing is technically 'blocked'. Many plans also stream video at reduced resolution by default. Check usage in the My Viasat app and compare this test at 3 am with 8 pm to see the effect."),
      ("Can I game or take video calls on Viasat?", "Video calls generally work — the high ping adds a noticeable delay but Zoom and Teams cope, and 3–5 Mbps upload is enough for one call at a time. Competitive online gaming is a different story: a 600 ms+ ping makes shooters and racing games unplayable, while turn-based and single-player games are fine. Watch jitter on this page too; satellite jitter above 50 ms is what makes calls stutter."),
      ("Is this affiliated with Viasat?", NOT_AFFIL)])

# US mobile / fixed-wireless
page("en", "verizon-5g-home-speed-test", "Verizon 5G Home", "Verizon 5G Home Internet Speed Test – Gateway Check | gbps.run",
     "Independent speed test for Verizon 5G Home and LTE Home Internet. See download, upload, ping and bufferbloat, and how gateway placement changes your result.",
     "Verizon 5G Home Internet speed test", "Verizon 5G Home runs over the same cellular network as your phone, so the number you get depends on signal, band and how busy the local tower is. Run this test with the gateway where it is now, move it to a different window, and run it again — then compare both results in the history below.",
     [("What speeds are normal on Verizon 5G Home?", "Verizon quotes typical download speeds roughly in the 85–300 Mbps range on 5G Home, with 5G Home Plus in strong Ultra Wideband (C-band or mmWave) areas commonly reaching 300–1,000 Mbps. Upload is typically 10–50 Mbps and ping 25–50 ms. LTE Home, sold where 5G isn't available, is usually 25–50 Mbps. Results swing through the day more than cable or fibre does, so a single reading means little — look at the range over several runs."),
      ("How do I get a faster result from the gateway?", "Placement decides almost everything. Put the gateway high up, on a window sill facing the nearest tower, away from metal blinds, TVs and thick exterior walls. The My Verizon app's setup tool shows signal strength and which band the gateway is locked to; a 5G UW connection on C-band is dramatically faster than low-band 5G or LTE. Each time you move it, give it a minute to re-register, then run this test again and compare."),
      ("Verizon 5G Home is fast in the morning but slow at night — why?", "Home gateways share tower capacity with every phone in the area, and in most markets Verizon deprioritises Home Internet traffic behind mobile customers when a tower is congested. That shows up as an evening drop of 30–60% while ping stays roughly the same. Use monitor mode on this page for a full day to see the pattern; if the daytime reading is healthy and the drop is purely evening, moving the gateway won't help much, but a different window sometimes reaches a less-loaded tower."),
      ("Is this affiliated with Verizon?", NOT_AFFIL)])
page("en", "spectrum-mobile-speed-test", "Spectrum Mobile", "Spectrum Mobile Speed Test – 5G Data Speed on Your Phone | gbps.run",
     "Test your Spectrum Mobile 5G or LTE speed in the browser, no app needed. See download, upload, ping and jitter, and why it can differ from Verizon's.",
     "Spectrum Mobile speed test", "Spectrum Mobile uses Verizon's towers plus Spectrum's own Wi‑Fi hotspots and, in some cities, Spectrum's own 5G spectrum. Switch off Wi‑Fi so the test uses cellular data, then run it — the download, ping and jitter numbers tell you what your phone's connection can really do right now.",
     [("What speeds should Spectrum Mobile give me?", "Because Spectrum Mobile runs on Verizon's network, speeds commonly track Verizon's: roughly 50–150 Mbps on low-band 5G and LTE, and 300 Mbps to 1 Gbps on 5G Ultra Wideband in cities and venues that have it. Upload is typically 10–40 Mbps and ping 25–45 ms. On the By the Gig plan and Unlimited plan, speeds are the same until you pass the monthly high-speed allowance, after which heavy users may be slowed."),
      ("Why is my Spectrum Mobile speed lower than my friend's Verizon?", "Spectrum Mobile is a mobile virtual network operator, so during congestion Verizon's own postpaid customers are typically served first and MVNO traffic may be deprioritised. At a quiet tower you'll see identical speeds; at a packed stadium or in the evening rush you may see less. Also check that your phone is actually on 5G UW (the icon shows UW) rather than low-band 5G, which is often no faster than LTE."),
      ("Does the test use Wi‑Fi or my Spectrum Mobile data?", "Whichever your phone is connected to. Spectrum Mobile phones auto-join Spectrum Wi‑Fi hotspots and your home Wi‑Fi, so turn Wi‑Fi off in Settings before testing if you want a true cellular reading. A full test uses roughly 100–400 MB depending on speed; pick the Quick setting in Settings if you're on the By the Gig plan."),
      ("Is this affiliated with Spectrum or Charter?", NOT_AFFIL)])
page("en", "visible-speed-test", "Visible", "Visible Speed Test – Is Visible Slower Than Verizon? | gbps.run",
     "Test your Visible Wireless speed on 5G or LTE in the browser. See download, upload, ping and jitter, and find out whether deprioritisation is slowing you down.",
     "Visible speed test", "Visible is Verizon-owned and runs on Verizon's towers, but its plans sit lower in the queue when a tower is busy. Turn Wi‑Fi off, run this test, and then run it again at a busy hour — the gap between the two is the deprioritisation Visible's cheaper plan trades for its price.",
     [("What speeds are normal on Visible?", "Visible speeds typically match Verizon's at quiet times: roughly 50–150 Mbps on LTE and low-band 5G, and 300 Mbps or more on 5G Ultra Wideband with the Visible+ plan. The base Visible plan can be slowed heavily on a congested tower — single-digit Mbps during an evening rush isn't unusual in dense cities. Upload commonly lands at 5–30 Mbps and ping at 25–50 ms. The hotspot on both plans is capped by Visible to a fixed rate, so don't judge the phone's own speed from a tethered laptop."),
      ("Why is Visible slow when my signal is full bars?", "Full bars mean a strong signal, not a free tower. Visible's base plan is deprioritised behind Verizon postpaid and most Verizon MVNO traffic whenever the cell is busy, so speed collapses at peak hours even though reception looks perfect. Run this test at 3 pm and again at 8 pm: a large drop with the same bars is deprioritisation, not a phone or settings problem. The Visible+ plan includes premium data on 5G UW that is far less affected."),
      ("How do I make Visible faster?", "Make sure 5G is enabled in your phone's cellular settings and that you're in a 5G UW area, since UW towers have far more capacity than LTE. Reset network settings if the phone sticks to LTE. If evening speeds are consistently unusable, the realistic fixes are the Visible+ plan or Wi‑Fi calling at home — a different window or restart won't change where you sit in the queue."),
      ("Is this affiliated with Visible or Verizon?", NOT_AFFIL)])
page("en", "mint-mobile-speed-test", "Mint Mobile", "Mint Mobile Speed Test – Real 5G Speed on T‑Mobile Towers | gbps.run",
     "Test your Mint Mobile 5G or LTE speed in the browser. See download, upload, ping and jitter, and learn when Mint is slowed behind T‑Mobile's own customers.",
     "Mint Mobile speed test", "Mint Mobile runs on T‑Mobile's towers, so your phone sees the same signal a T‑Mobile customer does — the difference is what happens when the tower is busy. Turn Wi‑Fi off and run the test; then run it again around 8 pm. The daytime number is your signal, and the gap to the evening number is the queue position Mint's price buys you.",
     [("What speeds should I expect on Mint Mobile?", "Because Mint uses T‑Mobile's network, uncongested speeds commonly match T‑Mobile's: roughly 50–150 Mbps on Extended Range (low-band) 5G and LTE, and 300–800 Mbps where Ultra Capacity (mid-band) 5G is available. Upload is typically 15–50 Mbps and ping 25–45 ms. All Mint plans include 5G at no extra cost, so a slow result is almost never a plan-tier limit — it is signal, band or congestion."),
      ("Why is Mint slower than T‑Mobile on the same tower?", "Mint traffic is deprioritised relative to T‑Mobile's postpaid customers whenever a cell is congested, so at a crowded venue or during the evening peak you may see a fraction of what a T‑Mobile phone next to you gets. When the tower has spare capacity the speeds are identical. If this test reads well at midday but drops sharply in the evening while the signal bars stay the same, that pattern is deprioritisation rather than a fault with your phone or SIM."),
      ("Mint is slow even with full bars — what should I check?", "First confirm the phone is actually on 5G UC, not plain 5G or LTE — Extended Range 5G is often no faster than 4G. In Settings, make sure 5G is enabled and that the Mint eSIM or SIM is the data line if you run two SIMs. Reset network settings if the phone sticks to LTE. Then check whether you have passed your plan's monthly high-speed allowance: Mint slows data heavily to a few hundred kbps after the cap, which looks exactly like a dead tower on a speed test."),
      ("Is this affiliated with Mint Mobile or T‑Mobile?", NOT_AFFIL)])
page("en", "cricket-speed-test", "Cricket", "Cricket Wireless Speed Test – Is Your Plan Capped? | gbps.run",
     "Test your Cricket Wireless 5G or LTE speed in the browser. See download, upload, ping and jitter, and find out whether a plan cap or congestion is the cause.",
     "Cricket Wireless speed test", "Cricket is owned by AT&T and runs on AT&T's towers, but not every Cricket plan gets the full speed of the network. Turn off Wi‑Fi and run the test. If your download flattens at a suspiciously round number in the single or low double digits regardless of signal, you are looking at a plan cap rather than a coverage problem.",
     [("What speeds are normal on Cricket?", "On Cricket's unlimited plans without a cap, speeds commonly match AT&T's: around 40–150 Mbps on LTE and low-band 5G, and 300 Mbps or more on AT&T 5G+ (mid-band) in cities that have it. Some of Cricket's cheaper plans have historically carried a fixed download ceiling, often 8 Mbps, which shows up here as a flat line at that value no matter how strong the signal is. Upload typically lands at 5–30 Mbps and ping at 30–50 ms."),
      ("Why does my Cricket speed stop at the same number every time?", "A result that repeatedly lands on the same figure — such as 8 Mbps — with excellent ping and no fluctuation is a plan-level cap, not a network issue. The tower could deliver far more; the plan simply does not allow it. Check your plan details in the Cricket app. If your plan is uncapped, the pattern is different: speeds vary widely with time of day and location rather than sitting on one number."),
      ("Is Cricket slower than AT&T itself?", "At a quiet tower an uncapped Cricket plan and an AT&T plan perform the same. When the cell is congested, Cricket traffic is deprioritised behind AT&T postpaid customers, so evening and event-time speeds can fall well below what an AT&T phone sees in the same spot. Run this test at a quiet hour and again at peak time: a large drop with unchanged signal bars is deprioritisation. 5G+ areas have far more capacity and are much less affected."),
      ("Is this affiliated with Cricket or AT&T?", NOT_AFFIL)])

# Problems / questions
page("en", "internet-slow-at-night", "Slow at night", "Why Is My Internet Slow at Night? Test & Fix the Dip | gbps.run",
     "Internet fast all day but slow after 7 pm? Measure the evening drop with a 24-hour monitor, learn why cable and 5G home congest, and what actually fixes it.",
     "Why is my internet slow at night?", "Run the test now, then turn on monitor mode below and leave this tab open until tomorrow morning. The chart that builds up shows exactly when speed falls and by how much. A dip that starts around 7 pm and recovers after 11 pm is neighbourhood congestion; a line that is slow at every hour is a different problem with a different fix.",
     [("How much of an evening slowdown is normal?", "On cable and fixed-wireless 5G home internet a 20–40% drop between 7 and 11 pm is common because the local node or tower is shared with your neighbours. Fibre to the home normally shows almost no evening dip — a few percent at most. If your evening speed is less than half of your daytime speed, or falls below what you need (about 25 Mbps per 4K stream), the provider's local capacity is oversubscribed and that is worth a complaint backed by your monitor log."),
      ("Is it my provider or my own Wi‑Fi?", "Evening is also when every neighbour's Wi‑Fi is busiest, so a 2.4 GHz network in a flat can crawl at night for reasons that have nothing to do with your line. To separate the two, run a wired Ethernet test during the slow period. If wired is still slow, it is the provider's network. If wired is fine but Wi‑Fi is poor, switch devices to the 5 GHz or 6 GHz band and pick a less crowded channel; the problem is in the air, not the line."),
      ("Why does ping get worse at night too?", "Congestion fills the queues in your provider's equipment, so packets wait longer before being sent: ping and jitter climb along with the speed drop. If this page shows a bufferbloat grade of C or worse at night, enabling SQM or QoS on your own router will not fix the provider's congestion, but it stops your household's own downloads from making the lag even worse during calls and games."),
      ("What can I actually do about it?", "Schedule big downloads, game updates and cloud backups for after midnight or early morning. Lower streaming quality on secondary TVs during peak hours. If you are on cable or 5G home internet and fibre is available at your address, fibre is the one change that reliably removes evening congestion. Otherwise, send your provider a week of monitor-mode results showing the pattern — a documented, repeatable evening drop is much harder for support to dismiss than 'it feels slow'.")])

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

page("es", "test-velocidad-gaming", "Gaming", "Test de velocidad para gaming – Ping, jitter y lag | gbps.run",
     "¿Tu internet sirve para jugar online? Mide ping, jitter, pérdida de paquetes, bufferbloat y velocidad de descarga para PS5, Xbox, Switch y PC.",
     "Test de internet para gaming", "El lag no depende de la velocidad de descarga. Depende del ping, el jitter, la pérdida de paquetes y de lo que le pasa a tu ping cuando alguien en casa empieza a descargar algo. Este test lo mide y lo califica todo.",
     [("¿Qué velocidad de internet necesito para jugar online?", "La mayoría de los juegos online usan menos de 1 Mbps. Lo que de verdad necesitas es un ping bajo (menos de 50 ms), poco jitter (menos de 15 ms), cero pérdida de paquetes y una nota de bufferbloat de B o mejor. La velocidad de descarga solo importa para instalar juegos y actualizaciones: con 100 Mbps, un juego de 80 GB tarda unas dos horas; con 500 Mbps, menos de media."),
      ("¿Por qué tengo lag si el test de velocidad sale rápido?", "Casi siempre es bufferbloat: el ping se dispara cuando la línea está ocupada, aunque la descarga sea de cientos de megas. Alguien viendo Netflix en 4K o subiendo fotos a la nube puede pasar tu ping de 20 ms a 300 ms. Fíjate en la nota de bufferbloat de esta página: con C o peor, activa SQM o QoS en el router y conecta la consola por cable. El Wi‑Fi de 2,4 GHz también añade jitter que el test de descarga no muestra."),
      ("¿Es mejor jugar por cable o por Wi‑Fi?", "Por cable, siempre que puedas. Ethernet quita entre 5 y 20 ms de ping respecto al Wi‑Fi y, sobre todo, elimina el jitter y las microcaídas que hacen que el juego 'rebote'. Si no hay más remedio que usar Wi‑Fi, usa la banda de 5 GHz o 6 GHz, pon la consola en la misma habitación que el router y evita que otros dispositivos descarguen mientras juegas."),
      ("¿Sirve el internet 5G en casa para jugar?", "Se puede jugar, pero el ping y el jitter son más altos y menos estables que con cable o fibra: 30–60 ms con picos es lo habitual, frente a 5–20 ms de la fibra. Para juegos competitivos conviene una conexión fija; para juegos casuales, de rol o por turnos no notarás gran diferencia.")], alt="gaming-speed-test")
page("es", "test-velocidad-videollamadas", "Videollamadas", "Test de velocidad para Zoom y Teams – Videollamadas | gbps.run",
     "Comprueba si tu conexión sirve para Zoom, Teams, Meet y FaceTime. Mide subida, ping, jitter y bufferbloat: las cuatro cosas que congelan una llamada.",
     "Test de internet para videollamadas", "Las llamadas no se congelan por falta de velocidad de descarga. Se congelan por la subida, el jitter y los picos de ping cuando alguien más usa la línea. Este test mide esas cuatro cosas y te da una respuesta clara antes de tu próxima reunión.",
     [("¿Qué velocidad necesita Zoom?", "Zoom recomienda unos 3–4 Mbps de subida y de bajada para llamadas grupales en HD; Teams y Google Meet piden cifras parecidas y FaceTime algo menos. Casi cualquier plan lo cumple de sobra. Lo que de verdad rompe una llamada es un jitter por encima de 30 ms, una pérdida de paquetes superior al 1% o un bufferbloat que dispara el ping cuando otra persona descarga algo en casa."),
      ("¿Por qué se congela mi imagen pero el audio sigue?", "Las aplicaciones sacrifican primero el vídeo cuando falta ancho de banda o el ping se dispara, y protegen el audio porque es lo más importante. Mira el jitter y la nota de bufferbloat de este test: si salen mal, acércate al router, usa la banda de 5 GHz o, mejor aún, un cable Ethernet, y activa QoS o SQM en el router para que las descargas de otros no te pisen la llamada."),
      ("¿Cuántas videollamadas a la vez aguanta mi conexión?", "Cuenta unos 4 Mbps de subida por llamada en HD. Con 10 Mbps de subida, dos personas teletrabajando van justas si además alguien sube fotos a la nube; con 20–30 Mbps de subida, tres o cuatro llamadas simultáneas van sobradas. En conexiones de cable o 4G/5G doméstico la subida suele ser la parte más escasa, así que ese es el número que debes mirar en el resultado, no la descarga."),
      ("¿Merece la pena usar cable para las reuniones importantes?", "Sí, sin duda. El Wi‑Fi añade jitter y microcortes por interferencias y retransmisiones, y eso es justo lo que se nota en una llamada. Un cable Ethernet entre el router y el portátil elimina ese problema de golpe y es la mejora más barata y efectiva para quien trabaja desde casa. Si no es posible, deja el portátil en la misma habitación que el router y evita el 2,4 GHz.")], alt="zoom-speed-test")
page("es", "test-velocidad-streaming-4k", "Streaming 4K", "Test de velocidad para 4K – Netflix, YouTube, Disney+ | gbps.run",
     "Averigua si tu internet puede reproducir 4K sin cortes. Mide la velocidad real y la estabilidad y calcula cuántas emisiones 4K simultáneas soporta tu casa.",
     "Test de velocidad para streaming 4K", "Una emisión en 4K necesita unos 25 Mbps estables, no solo en el pico. Este test mide tu velocidad de descarga real y su constancia, y te dice cuántas pantallas en 4K puedes tener reproduciendo a la vez sin que ninguna se quede cargando.",
     [("¿Cuánta velocidad hace falta para ver en 4K?", "Netflix recomienda unos 15 Mbps para 4K, YouTube alrededor de 20 Mbps y Disney+ y Prime Video cifras similares; 25 Mbps es un margen seguro que cubre también el contenido con bitrate alto, como HDR o Dolby Vision. Multiplica por el número de televisores que suelen verse a la vez: tres pantallas en 4K y una videollamada van cómodas con 100 Mbps reales, no de plan."),
      ("¿Por qué se queda cargando Netflix si mi velocidad es buena?", "Porque lo que importa es la estabilidad, no el máximo. Si en este test la puntuación de consistencia sale baja, la señal está cayendo a ratos por interferencias de Wi‑Fi, por un vecino en el mismo canal o por congestión de la línea a las 9 de la noche. Prueba la banda de 5 GHz, acerca el router al televisor o pásale un cable, y repite el test a la hora en que suele fallar."),
      ("¿Influye el Wi‑Fi del propio televisor?", "Mucho. Bastantes televisores llevan Wi‑Fi solo de 2,4 GHz o antenas muy flojas, así que reciben una fracción de lo que el router entrega. Un cable Ethernet hasta el televisor, o un reproductor externo como un Fire TV o Apple TV conectado a 5 GHz, resuelve la mayoría de los cortes sin tocar el contrato con el operador."),
      ("¿Puedo ver 4K con internet por 4G o 5G en casa?", "Normalmente sí para una pantalla, ya que 50–150 Mbps son habituales, pero la velocidad varía mucho con la hora y la saturación de la antena, y las noches suelen ser el momento más flojo. Si el test muestra buena velocidad pero poca constancia, la reproducción bajará a 1080p de vez en cuando; una posición mejor del router cerca de una ventana suele estabilizarla.")], alt="4k-streaming-speed-test")
page("es", "test-velocidad-gigabit", "Gigabit", "Test de velocidad gigabit – ¿Tu fibra de 1 Gbps rinde? | gbps.run",
     "Test de velocidad preciso para fibra de 1 Gbps o más. Varias conexiones en paralelo para medir bien a gigabit, comparación con tu plan y límites del hardware.",
     "Test de velocidad gigabit", "La mayoría de los tests se quedan cortos con la fibra de 1 Gbps. Este abre hasta ocho conexiones en paralelo y descarta el arranque, así que mide bien a 1 Gbps y por encima. Tu plan ya está preajustado a 1.000 Mbps más abajo: si el resultado por cable ronda los 900–940 Mbps, estás recibiendo todo lo que pagas.",
     [("¿Por qué mi fibra de 1 Gbps mide 940 Mbps y no 1.000?", "Porque 940 Mbps es el máximo útil de un puerto Ethernet gigabit una vez descontada la cabecera de los protocolos. No es una pérdida: es la señal de que la línea entrega el plan completo. Muchos operadores entregan algo más de 1 Gbps en el router precisamente para que un equipo con puerto gigabit llegue a esos ~940."),
      ("¿Qué Wi‑Fi necesito para aprovechar el gigabit?", "Un router Wi‑Fi 6, 6E o 7 con canales de 160 MHz activados, y un móvil o portátil que los admita (la mayoría de los fabricados desde 2021). En la misma habitación es razonable esperar 600–900 Mbps; a una pared de distancia, bastante menos. Con el Wi‑Fi 5 de muchos routers de operador rara vez pasarás de 300–500 Mbps, aunque la fibra sea perfecta."),
      ("El test da 300 Mbps por cable, ¿qué reviso?", "Primero el cable y el puerto: un cable Cat 5e o superior y un puerto gigabit en el router y en el ordenador. Si el ordenador negocia a 100 Mbps, el resultado se queda clavado en unos 94 Mbps. Después, cierra copias en la nube y descargas que estén en marcha, y repite. Si sigue bajo con todo correcto, pide al operador que compruebe el perfil de la ONT: a veces la línea sigue provisionada en el plan antiguo."),
      ("¿Cómo mido por encima de 1 Gbps?", "Hacen falta un puerto de 2,5 o 10 GbE en el ordenador, un puerto multigigabit en el router y un equipo reciente. Los navegadores suelen topar en torno a 2–3 Gbps; para más, usa una herramienta de línea de comandos como iperf3 contra un servidor adecuado.")], plan=1000, alt="gigabit-speed-test")
page("es", "test-velocidad-5g", "5G / móvil", "Test de velocidad 5G – Datos móviles en iPhone y Android | gbps.run",
     "Mide la velocidad de tu 5G o 4G desde el navegador, sin instalar nada. Descarga, subida, ping y jitter de la conexión móvil de tu teléfono y qué es normal.",
     "Test de velocidad 5G", "Desactiva el Wi‑Fi y lanza el test para medir la conexión 5G o 4G de tu móvil. No hace falta ninguna app ni permiso. Fíjate en el icono de la barra de estado: el 5G de banda baja va poco más rápido que el 4G, y la diferencia de verdad la marca el 5G en la banda de 3,5 GHz.",
     [("¿Qué velocidad es normal en 5G?", "En 5G de banda baja (el que a veces se muestra como 5G sobre una red 4G) lo habitual son 50–150 Mbps. En la banda de 3,5 GHz, la que los operadores despliegan en ciudades, es común ver 300–1.000 Mbps en buenas condiciones. La subida suele quedarse en 10–50 Mbps y el ping en 20–40 ms. En 4G, 20–80 Mbps es un resultado normal."),
      ("¿Cuántos datos gasta el test?", "Depende de la velocidad: en una conexión rápida, entre 100 y 400 MB, porque el test se adapta a lo que da la línea. Si tienes una tarifa con pocos gigas, elige la duración Rápida en Ajustes antes de empezar, o repite el test solo cuando lo necesites."),
      ("¿Por qué mi 5G va lento dentro de casa?", "Las frecuencias altas del 5G atraviesan mal paredes y ventanas con tratamiento térmico, así que el móvil suele caer a 4G o a 5G de banda baja al entrar en un edificio. Prueba junto a una ventana y luego en el interior: si la diferencia es grande, el problema es la cobertura dentro, no el operador. Una cobertura buena en la calle no garantiza nada en el salón."),
      ("¿Por qué el ping del 5G es mayor que el de la fibra?", "La red móvil añade por naturaleza unos 20–40 ms frente a los 5–15 ms de una fibra en casa. Para navegar, ver vídeo y llamadas no se nota; para juegos competitivos se percibe. Si el ping sube mucho con la línea cargada (mira la nota de bufferbloat), la antena está saturada y la hora del día influye más que el móvil.")], alt="5g-speed-test")

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


# ---- India build: ISPs, 5G, gaming, problems (English = where most Indian search volume is)
page("en", "bsnl-speed-test", "BSNL", "BSNL Speed Test – Bharat Fibre & BSNL 4G | gbps.run",
     "Independent speed test for BSNL Bharat Fibre (FTTH) and BSNL 4G/5G. Check download, upload, ping and bufferbloat and compare with your plan.",
     "BSNL speed test", "For BSNL Bharat Fibre and BSNL mobile users. Run the test, enter your plan and see the percentage you actually receive.",
     [("What speeds should BSNL Bharat Fibre give?", "Bharat Fibre plans commonly range from 30 Mbps to 300 Mbps, with some 1 Gbps tiers in select circles. A wired test at 80–95% of the plan is normal; many BSNL FTTH plans have lower upload than download, so don't be alarmed if upload is smaller."),
      ("Why is BSNL fibre slow in the evening?", "Local exchange congestion is common on BSNL at peak hours. Use monitor mode on this page to log a day of results — a clear evening dip is useful evidence when you raise a complaint."),
      ("Is this the official BSNL speed test?", NOT_AFFIL)])
page("en", "vi-speed-test", "Vi", "Vi Speed Test – Vodafone Idea 4G & Vi 5G | gbps.run",
     "Speed test for Vi (Vodafone Idea) 4G and Vi 5G. Measure download, upload, ping and jitter on your phone's mobile data — no app required.",
     "Vi speed test", "Switch off Wi‑Fi, then run the test to measure your Vi 4G or 5G connection. No app, no permissions.",
     [("What Vi speeds are normal?", "Vi 4G typically delivers 10–60 Mbps depending on the city and time of day; Vi 5G, where available, is often 100–500 Mbps. Ping of 30–60 ms is typical on mobile."),
      ("Why is my Vi speed low?", "Signal strength, indoor location and tower congestion matter most. Test near a window, compare times of day, and check whether your phone is on 4G or 5G in the status bar."),
      ("Is this affiliated with Vi?", NOT_AFFIL)])
page("en", "act-fibernet-speed-test", "ACT Fibernet", "ACT Fibernet Speed Test – Check Your Real Speed | gbps.run",
     "Independent speed test for ACT Fibernet. Check download, upload, ping and bufferbloat, and compare with your 100 Mbps, 300 Mbps or 1 Gbps plan.",
     "ACT Fibernet speed test", "For ACT Fibernet users in Bengaluru, Hyderabad, Chennai, Delhi and other cities. Enter your plan after the test to see what you're really getting.",
     [("What speeds should ACT Fibernet deliver?", "ACT plans run from around 50 Mbps to 1 Gbps and are symmetrical on most tiers, so upload should be close to download. A wired test at 85–95% of the plan is normal; Wi‑Fi on the ACT router is often lower in far rooms."),
      ("ACT is slow on Wi‑Fi but fine on cable — why?", "The router, not the line. Use the 5 GHz band, move the router into the open, or replace the ISP router with a Wi‑Fi 6 model."),
      ("Is this the official ACT speed test?", NOT_AFFIL)])
page("en", "hathway-speed-test", "Hathway", "Hathway Speed Test – Cable Broadband Check | gbps.run",
     "Independent speed test for Hathway broadband. Download, upload, ping and bufferbloat with plan comparison.",
     "Hathway speed test", "For Hathway broadband users. Run the test, enter your plan and check whether the shortfall is your Wi‑Fi or the line.",
     [("What speeds should Hathway give?", "Hathway plans typically range from 50 Mbps to 300 Mbps, with upload usually lower than download on cable. Wired tests at 80–95% of plan are normal."),
      ("Is this affiliated with Hathway?", NOT_AFFIL)])
page("en", "tata-play-fiber-speed-test", "Tata Play Fiber", "Tata Play Fiber Speed Test – Symmetrical Fibre Check | gbps.run",
     "Speed test for Tata Play Fiber. Check symmetrical download and upload, ping, jitter and bufferbloat.",
     "Tata Play Fiber speed test", "Tata Play Fiber is symmetrical fibre, so your upload should be close to your download. If it isn't, the limit is on your side of the ONT.",
     [("What speeds should Tata Play Fiber show?", "Plans typically range from 100 Mbps to 1 Gbps, symmetrical. A 1 Gbps plan shows about 900–940 Mbps on a gigabit Ethernet port; over Wi‑Fi expect 300–800 Mbps depending on the router."),
      ("Is this affiliated with Tata Play?", NOT_AFFIL)])
page("en", "excitel-speed-test", "Excitel", "Excitel Speed Test – 200/300/400 Mbps Plan Check | gbps.run",
     "Independent speed test for Excitel broadband. Check download, upload, ping and bufferbloat and compare with your 200, 300 or 400 Mbps plan.",
     "Excitel speed test", "For Excitel users in Delhi NCR, Hyderabad, Bengaluru and other cities. Enter your plan after the test to see the percentage delivered.",
     [("What speeds should Excitel deliver?", "Excitel's popular plans are 200, 300 and 400 Mbps, generally symmetrical. Wired tests at 85–95% are normal; Excitel's shared local networks can dip at peak hours."),
      ("Is this affiliated with Excitel?", NOT_AFFIL)])
page("en", "jio-5g-speed-test", "Jio 5G", "Jio 5G Speed Test – True 5G Speed on Your Phone | gbps.run",
     "Test your Jio True 5G speed in the browser. Download, upload, ping and jitter — and why 5G speed changes so much from place to place.",
     "Jio 5G speed test", "Turn off Wi‑Fi and make sure the status bar shows 5G, then run the test. Jio True 5G on the n78 band can be very fast; low-band 5G is not.",
     [("What Jio 5G speeds are normal?", "On the n78 (3.5 GHz) band, 200–800 Mbps download is common, with uploads of 20–80 Mbps. On n28 low-band or in weak signal, speeds fall to 4G-like levels. Ping is usually 20–40 ms."),
      ("Why does my Jio 5G speed vary so much?", "Band, signal strength and tower load. Indoors you often drop to low-band; near a window or outdoors you get n78. Test both and you'll see the difference."),
      ("Is this the official Jio speed test?", NOT_AFFIL)])
page("en", "airtel-5g-speed-test", "Airtel 5G", "Airtel 5G Plus Speed Test | gbps.run",
     "Test your Airtel 5G Plus speed in the browser — download, upload, ping and jitter, with tips on why 5G speed varies.",
     "Airtel 5G speed test", "Turn off Wi‑Fi and check the status bar shows 5G, then run the test. Airtel 5G Plus uses the n78 band for its highest speeds.",
     [("What Airtel 5G speeds are normal?", "Commonly 150–600 Mbps download on n78 with 20–60 Mbps upload; much lower on low-band or weak signal. Ping of 20–40 ms is typical."),
      ("Airtel 5G shows but speed is like 4G — why?", "Your phone may be on NSA 5G with the data actually flowing over 4G, or on a congested tower. Try a different location and time; compare with the Jio 5G test if you have both."),
      ("Is this affiliated with Airtel?", NOT_AFFIL)])
page("en", "jiofiber-slow", "JioFiber slow?", "JioFiber Slow? Test It and Fix It in 5 Minutes | gbps.run",
     "JioFiber slower than your plan? Run the test, see whether it's Wi‑Fi, the ONT/router or the line, and follow the fixes that actually work.",
     "Is your JioFiber slow? Test and fix", "Run the test on Wi‑Fi, then on a LAN cable if you can. If the cable test is near your plan, the fix is on your side — and it's usually one of the three things below.",
     [("JioFiber is slow on Wi‑Fi but fast on cable", "The Jio router's Wi‑Fi is the limit. Put devices on the 5 GHz network (not 2.4), move the router into the open, and for plans above 300 Mbps use your own Wi‑Fi 6 router behind the Jio ONT."),
      ("JioFiber is slow on cable too", "Restart the ONT (unplug 30 s). Check the fibre light is solid green, not red (LOS). Test at a quiet time; if it stays low, raise a ticket in the MyJio app with your results — Copy as CSV on this page gives you the evidence."),
      ("JioFiber slow only in the evening", "Peak-hour congestion. Use monitor mode here to log a full day; a consistent 7–11 pm drop is worth escalating."),
      ("Is this affiliated with Jio?", NOT_AFFIL)])
page("en", "bgmi-ping-test", "BGMI ping", "BGMI Ping Test – Check Your Lag Before You Play | gbps.run",
     "Free BGMI ping test. Measure ping, jitter, packet loss and ping under load in your browser, and learn what ping you need for BGMI and how to lower it.",
     "BGMI ping test", "Lag in BGMI is about ping, jitter and packet loss — not download speed. This test measures all three, plus what happens to your ping when someone else in the house starts a download.",
     [("What ping is good for BGMI?", "Under 40 ms is excellent, 40–80 ms is fine, 80–150 ms is playable with some delay, over 150 ms is laggy. Jitter under 15 ms keeps gunfights fair."),
      ("How do I lower my BGMI ping?", "Use 5 GHz Wi‑Fi or a LAN cable to the phone (USB‑C adapter), sit near the router, close background downloads, and pick the nearest game server (Asia/India). If the bufferbloat grade here is C or worse, enable QoS on the router."),
      ("Is this ping to BGMI's servers?", "No — it's to the nearest Cloudflare data centre in India (Mumbai, Delhi, Chennai, Bengaluru, Hyderabad, Kolkata). BGMI's own servers add a little on top, so treat this as your baseline.")])
page("en", "free-fire-ping-test", "Free Fire ping", "Free Fire Ping Test – Fix Lag on Mobile | gbps.run",
     "Free Fire ping test in your browser: ping, jitter, packet loss and ping under load, with tips to reduce lag on Jio, Airtel and Vi.",
     "Free Fire ping test", "Free Fire feels laggy on high ping and jitter. Test your connection here on Wi‑Fi and on mobile data, and use the lower one.",
     [("What ping is good for Free Fire?", "Under 50 ms is great, 50–100 ms is fine, over 150 ms is noticeable lag. Jitter under 15 ms matters as much as the ping itself."),
      ("Mobile data or Wi‑Fi for Free Fire?", "Whichever gives lower jitter here. 5G often has lower ping than a congested home Wi‑Fi; a good 5 GHz Wi‑Fi near the router usually beats 4G."),
      ("How do I reduce Free Fire lag?", "Close background apps and downloads, switch to 5 GHz Wi‑Fi, select the India server in game, and if your router's bufferbloat grade is poor, enable QoS.")])

# Outage pages for India
for slug, isp, st in [("is-jio-down", "Jio", "MyJio app / jio.com"), ("is-airtel-down", "Airtel", "Airtel Thanks app")]:
    page("en", slug, f"Is {isp} down?", f"Is {isp} Down Right Now? Live Check | gbps.run",
         f"Check in seconds whether {isp} is down for you or everyone. Live connectivity test, then a full speed test to tell an outage from slow Wi‑Fi or congestion.",
         f"Is {isp} down right now?", f"This page checks your connection automatically. Then run the full test to tell an outage from slow Wi‑Fi. Official status: {st}.", OUT_FAQ(isp, st), mode="outage")

# Hindi versions of the key India pages
page("hi", "bsnl-speed-test", "BSNL", "BSNL स्पीड टेस्ट – Bharat Fibre और BSNL 4G | gbps.run",
     "BSNL Bharat Fibre (FTTH) और BSNL 4G/5G के लिए स्वतंत्र स्पीड टेस्ट। डाउनलोड, अपलोड, पिंग और बफरब्लोट जाँचें और अपने प्लान से तुलना करें।",
     "BSNL स्पीड टेस्ट", "BSNL Bharat Fibre और BSNL मोबाइल यूज़र्स के लिए। टेस्ट करें, अपना प्लान डालें और देखें कि असल में कितना प्रतिशत मिल रहा है।",
     [("BSNL Bharat Fibre में कितनी स्पीड मिलनी चाहिए?", "Bharat Fibre प्लान आमतौर पर 30 Mbps से 300 Mbps तक होते हैं, कुछ सर्किल में 1 Gbps भी। LAN पर प्लान का 80–95% सामान्य है; कई BSNL FTTH प्लान में अपलोड, डाउनलोड से कम होता है।"),
      ("शाम को BSNL फ़ाइबर धीमा क्यों?", "पीक समय पर लोकल एक्सचेंज में भीड़ आम है। इस पेज पर मॉनिटर मोड से पूरे दिन का लॉग रखें — शाम की साफ़ गिरावट शिकायत में काम आती है।"),
      ("क्या यह BSNL का आधिकारिक टेस्ट है?", "नहीं। gbps.run स्वतंत्र है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="bsnl-speed-test")
page("hi", "vi-speed-test", "Vi", "Vi स्पीड टेस्ट – Vodafone Idea 4G और Vi 5G | gbps.run",
     "Vi (Vodafone Idea) 4G और Vi 5G के लिए स्पीड टेस्ट। फ़ोन के मोबाइल डेटा पर डाउनलोड, अपलोड, पिंग और जिटर मापें — कोई ऐप नहीं।",
     "Vi स्पीड टेस्ट", "Wi‑Fi बंद करें और Vi 4G या 5G कनेक्शन मापने के लिए टेस्ट चलाएँ। कोई ऐप नहीं, कोई परमिशन नहीं।",
     [("Vi की सामान्य स्पीड कितनी है?", "Vi 4G आमतौर पर शहर और समय के हिसाब से 10–60 Mbps देता है; जहाँ Vi 5G है वहाँ अक्सर 100–500 Mbps। मोबाइल पर 30–60 ms पिंग सामान्य है।"),
      ("मेरी Vi स्पीड कम क्यों है?", "सिग्नल, इनडोर लोकेशन और टावर पर भीड़ सबसे ज़्यादा मायने रखते हैं। खिड़की के पास टेस्ट करें, अलग समय पर तुलना करें, और स्टेटस बार में देखें कि फ़ोन 4G पर है या 5G पर।")], alt="vi-speed-test")
page("hi", "jio-5g-speed-test", "Jio 5G", "Jio 5G स्पीड टेस्ट – अपने फ़ोन पर True 5G स्पीड | gbps.run",
     "ब्राउज़र में Jio True 5G स्पीड टेस्ट करें। डाउनलोड, अपलोड, पिंग और जिटर — और 5G स्पीड जगह-जगह इतनी क्यों बदलती है।",
     "Jio 5G स्पीड टेस्ट", "Wi‑Fi बंद करें, स्टेटस बार में 5G दिखे यह पक्का करें, फिर टेस्ट चलाएँ। n78 बैंड पर Jio True 5G बहुत तेज़ हो सकता है; लो-बैंड 5G नहीं।",
     [("Jio 5G की सामान्य स्पीड कितनी है?", "n78 (3.5 GHz) बैंड पर 200–800 Mbps डाउनलोड आम है, अपलोड 20–80 Mbps। n28 लो-बैंड या कमज़ोर सिग्नल में स्पीड 4G जैसी हो जाती है। पिंग आमतौर पर 20–40 ms।"),
      ("मेरी Jio 5G स्पीड इतनी क्यों बदलती है?", "बैंड, सिग्नल और टावर लोड। घर के अंदर अक्सर लो-बैंड मिलता है; खिड़की के पास या बाहर n78। दोनों जगह टेस्ट करें, फ़र्क दिखेगा।")], alt="jio-5g-speed-test")
page("hi", "airtel-5g-speed-test", "Airtel 5G", "Airtel 5G Plus स्पीड टेस्ट | gbps.run",
     "ब्राउज़र में Airtel 5G Plus स्पीड टेस्ट — डाउनलोड, अपलोड, पिंग और जिटर, साथ में 5G स्पीड बदलने की वजहें।",
     "Airtel 5G स्पीड टेस्ट", "Wi‑Fi बंद करें और स्टेटस बार में 5G देखें, फिर टेस्ट चलाएँ। Airtel 5G Plus सबसे तेज़ स्पीड के लिए n78 बैंड इस्तेमाल करता है।",
     [("Airtel 5G की सामान्य स्पीड कितनी है?", "n78 पर आमतौर पर 150–600 Mbps डाउनलोड और 20–60 Mbps अपलोड; लो-बैंड या कमज़ोर सिग्नल में काफ़ी कम। 20–40 ms पिंग सामान्य है।"),
      ("5G दिखता है पर स्पीड 4G जैसी — क्यों?", "फ़ोन NSA 5G पर हो सकता है जहाँ डेटा असल में 4G से जाता है, या टावर व्यस्त है। दूसरी जगह और समय पर आज़माएँ।")], alt="airtel-5g-speed-test")
page("hi", "bgmi-ping-test", "BGMI पिंग", "BGMI पिंग टेस्ट – खेलने से पहले लैग जाँचें | gbps.run",
     "मुफ़्त BGMI पिंग टेस्ट। ब्राउज़र में पिंग, जिटर, पैकेट लॉस और लोड के साथ पिंग मापें, और जानें BGMI के लिए कितना पिंग चाहिए और उसे कैसे घटाएँ।",
     "BGMI पिंग टेस्ट", "BGMI में लैग पिंग, जिटर और पैकेट लॉस से होता है — डाउनलोड स्पीड से नहीं। यह टेस्ट तीनों मापता है, और यह भी कि घर में कोई डाउनलोड शुरू करे तो आपके पिंग का क्या होता है।",
     [("BGMI के लिए अच्छा पिंग कितना है?", "40 ms से कम बेहतरीन, 40–80 ms ठीक, 80–150 ms थोड़ी देरी के साथ खेलने लायक, 150 ms से ऊपर लैग। 15 ms से कम जिटर गनफ़ाइट को फ़ेयर रखता है।"),
      ("BGMI का पिंग कैसे घटाएँ?", "5 GHz Wi‑Fi या फ़ोन में LAN केबल (USB‑C अडैप्टर) इस्तेमाल करें, राउटर के पास बैठें, बैकग्राउंड डाउनलोड बंद करें, और गेम में नज़दीकी सर्वर (Asia/India) चुनें। बफरब्लोट ग्रेड C या खराब हो तो राउटर में QoS चालू करें।"),
      ("क्या यह BGMI सर्वर तक का पिंग है?", "नहीं — यह भारत में नज़दीकी Cloudflare डेटा सेंटर (मुंबई, दिल्ली, चेन्नई, बेंगलुरु, हैदराबाद, कोलकाता) तक है। BGMI के सर्वर थोड़ा और जोड़ते हैं, इसलिए इसे बेसलाइन मानें।")], alt="bgmi-ping-test")
page("hi", "jiofiber-slow", "JioFiber धीमा?", "JioFiber धीमा चल रहा है? 5 मिनट में टेस्ट और फ़िक्स करें | gbps.run",
     "JioFiber प्लान से धीमा? टेस्ट करें, जानें कि समस्या Wi‑Fi है, ONT/राउटर है या लाइन, और वो फ़िक्स अपनाएँ जो सच में काम करते हैं।",
     "क्या आपका JioFiber धीमा है? टेस्ट करें और ठीक करें", "पहले Wi‑Fi पर टेस्ट करें, फिर हो सके तो LAN केबल पर। अगर केबल पर स्पीड प्लान के पास है, तो समस्या आपकी तरफ़ है — और आमतौर पर नीचे की तीन चीज़ों में से एक।",
     [("JioFiber Wi‑Fi पर धीमा, केबल पर तेज़", "Jio राउटर का Wi‑Fi ही सीमा है। डिवाइस 5 GHz नेटवर्क पर रखें (2.4 नहीं), राउटर खुली जगह रखें, और 300 Mbps से ऊपर के प्लान में Jio ONT के पीछे अपना Wi‑Fi 6 राउटर लगाएँ।"),
      ("केबल पर भी धीमा", "ONT रीस्टार्ट करें (30 सेकंड अनप्लग)। फ़ाइबर लाइट हरी (solid) हो, लाल (LOS) नहीं। शांत समय पर टेस्ट करें; फिर भी कम हो तो MyJio ऐप में टिकट डालें — इस पेज का \"CSV कॉपी करें\" आपका सबूत है।"),
      ("सिर्फ़ शाम को धीमा", "पीक-ऑवर भीड़। यहाँ मॉनिटर मोड से पूरे दिन का लॉग रखें; हर दिन 7–11 बजे की गिरावट शिकायत लायक है।")], alt="jiofiber-slow")

page("hi", "act-fibernet-speed-test", "ACT Fibernet", "ACT Fibernet स्पीड टेस्ट – असली स्पीड जाँचें | gbps.run",
     "ACT Fibernet के लिए स्वतंत्र स्पीड टेस्ट। डाउनलोड, अपलोड, पिंग और बफरब्लोट मापें और अपने 100 Mbps, 300 Mbps या 1 Gbps प्लान से तुलना करें — Wi‑Fi और LAN पर।",
     "ACT Fibernet स्पीड टेस्ट", "बेंगलुरु, हैदराबाद, चेन्नई और दिल्ली के ACT Fibernet यूज़र्स के लिए। टेस्ट चलाएँ, अपना प्लान डालें और देखें कि असल में कितना प्रतिशत मिल रहा है — अपलोड पर भी नज़र रखें, ACT पर वह डाउनलोड के बराबर होना चाहिए।",
     [("ACT Fibernet में कितनी स्पीड मिलनी चाहिए?", "ACT के प्लान आमतौर पर 50 Mbps से 1 Gbps तक होते हैं और ज़्यादातर टियर सिमेट्रिकल हैं, यानी अपलोड भी डाउनलोड के करीब होना चाहिए। LAN केबल पर प्लान का 85–95% सामान्य है। अगर 300 Mbps के प्लान पर Wi‑Fi से 90–100 Mbps ही आ रहा है, तो रुकावट लगभग हमेशा राउटर या फ़ोन का Wi‑Fi है, लाइन नहीं।"),
      ("ACT Wi‑Fi पर धीमा लेकिन केबल पर ठीक — क्यों?", "समस्या राउटर की है, लाइन की नहीं। फ़ोन को 5 GHz नेटवर्क से जोड़ें (नाम में अक्सर 5G लिखा होता है), राउटर को अलमारी से निकालकर खुली जगह रखें, और 300 Mbps से ऊपर के प्लान पर ACT के दिए राउटर की जगह Wi‑Fi 6 राउटर लगाएँ। पुराने फ़ोन 2.4 GHz पर 40–70 Mbps से ऊपर जा ही नहीं पाते।"),
      ("शाम को ACT की स्पीड क्यों गिरती है?", "ACT फ़ाइबर है, इसलिए शाम की गिरावट केबल ब्रॉडबैंड जितनी नहीं होती, पर अपार्टमेंट में एक ही स्विच पर कई घर होने से 8–11 बजे भीड़ हो सकती है। इस पेज पर मॉनिटर मोड चलाकर पूरे दिन का लॉग रखें; हर रोज़ एक ही समय पर 30–40% की गिरावट ACT ऐप में शिकायत के लिए ठोस सबूत है।"),
      ("क्या यह ACT का आधिकारिक स्पीड टेस्ट है?", "नहीं। gbps.run स्वतंत्र है, विज्ञापन-मुक्त है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="act-fibernet-speed-test")
page("hi", "hathway-speed-test", "Hathway", "Hathway स्पीड टेस्ट – केबल ब्रॉडबैंड जाँचें | gbps.run",
     "Hathway ब्रॉडबैंड के लिए स्वतंत्र स्पीड टेस्ट। डाउनलोड, अपलोड, पिंग और बफरब्लोट मापें, प्लान से तुलना करें और जानें कि कमी Wi‑Fi की है या लाइन की।",
     "Hathway स्पीड टेस्ट", "Hathway केबल और फ़ाइबर ब्रॉडबैंड यूज़र्स के लिए। टेस्ट करें, अपना प्लान डालें, और फिर LAN केबल पर दोबारा टेस्ट करें — दोनों नंबरों का फ़र्क बताता है कि समस्या आपके घर में है या Hathway की तरफ़।",
     [("Hathway में कितनी स्पीड मिलनी चाहिए?", "Hathway के प्लान आमतौर पर 50 Mbps से 300 Mbps के बीच होते हैं; कुछ शहरों में फ़ाइबर पर 500 Mbps–1 Gbps भी। केबल कनेक्शन पर अपलोड डाउनलोड से काफ़ी कम रहता है — 100 Mbps प्लान पर 10–30 Mbps अपलोड सामान्य है। LAN पर प्लान का 80–95% ठीक माना जाता है।"),
      ("Hathway शाम को इतना धीमा क्यों हो जाता है?", "केबल ब्रॉडबैंड में एक ही नोड पर कई घर जुड़े होते हैं, इसलिए 8–11 बजे की भीड़ आम है। अगर दोपहर में 95 Mbps और रात में 30 Mbps मिलता है, तो यह नोड की भीड़ है, आपका राउटर नहीं। यहाँ मॉनिटर मोड से कुछ दिन का लॉग रखें और Hathway ऐप में टिकट के साथ CSV लगाएँ।"),
      ("सबसे पहले क्या जाँचें?", "मॉडेम/ONT और राउटर दोनों को 30 सेकंड अनप्लग करके रीस्टार्ट करें, फिर एक डिवाइस LAN केबल से जोड़कर टेस्ट करें। केबल पर स्पीड प्लान के पास हो तो समस्या Wi‑Fi है — 5 GHz बैंड पर जाएँ और राउटर खुली जगह रखें। केबल पर भी कम हो और पिंग 50 ms से ऊपर हो, तो लाइन की शिकायत करें।"),
      ("क्या यह Hathway का आधिकारिक टेस्ट है?", "नहीं। gbps.run स्वतंत्र है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="hathway-speed-test")
page("hi", "tata-play-fiber-speed-test", "Tata Play Fiber", "Tata Play Fiber स्पीड टेस्ट – सिमेट्रिकल फ़ाइबर जाँचें | gbps.run",
     "Tata Play Fiber के लिए स्वतंत्र स्पीड टेस्ट। डाउनलोड, अपलोड, पिंग, जिटर और बफरब्लोट मापें और 100 Mbps, 300 Mbps या 1 Gbps प्लान से तुलना करें — Wi‑Fi और LAN पर।",
     "Tata Play Fiber स्पीड टेस्ट", "Tata Play Fiber पूरी तरह फ़ाइबर (FTTH) है और इसके प्लान सिमेट्रिकल हैं, यानी अपलोड भी डाउनलोड के बराबर मिलना चाहिए। टेस्ट चलाएँ, प्लान डालें और दोनों नंबर देखें — अगर अपलोड बहुत कम है, तो रुकावट ONT के आपकी तरफ़ वाले हिस्से में है।",
     [("Tata Play Fiber में कितनी स्पीड मिलनी चाहिए?", "प्लान आमतौर पर 100 Mbps से 1 Gbps तक होते हैं और डाउनलोड-अपलोड बराबर रहते हैं। 1 Gbps प्लान LAN पर करीब 900–940 Mbps दिखाता है क्योंकि गीगाबिट पोर्ट की यही सीमा है; Wi‑Fi पर राउटर के हिसाब से 300–800 Mbps सामान्य है। 300 Mbps प्लान पर LAN से 270–295 Mbps ठीक माना जाता है।"),
      ("अपलोड डाउनलोड से बहुत कम आ रहा है — क्यों?", "फ़ाइबर पर ऐसा नहीं होना चाहिए। पहले फ़ोन की जगह लैपटॉप से LAN केबल पर टेस्ट करें — फ़ोन का Wi‑Fi अपलोड अक्सर डाउनलोड से कमज़ोर होता है। केबल पर भी अपलोड कम हो तो ONT रीस्टार्ट करें और Tata Play Fiber ऐप से चेक करें कि प्लान सही प्रोविज़न हुआ है; कई बार पुराने प्लान की अपलोड सीमा बनी रह जाती है।"),
      ("सबसे पहले क्या जाँचें?", "ONT पर PON लाइट हरी और LOS लाइट बंद होनी चाहिए; LOS लाल जले तो फ़ाइबर में दिक्कत है और टिकट ही रास्ता है। लाइटें ठीक हों तो राउटर को 5 GHz बैंड पर रखें, और 300 Mbps से ऊपर के प्लान पर दिए हुए राउटर की जगह Wi‑Fi 6 राउटर लगाने से अक्सर दोगुना फ़र्क पड़ता है। इस पेज पर पिंग 10–30 ms और बफरब्लोट ग्रेड A या B आना चाहिए।"),
      ("क्या यह Tata Play का आधिकारिक टेस्ट है?", "नहीं। gbps.run स्वतंत्र है, विज्ञापन-मुक्त है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="tata-play-fiber-speed-test")
page("hi", "excitel-speed-test", "Excitel", "Excitel स्पीड टेस्ट – 200/300/400 Mbps प्लान जाँचें | gbps.run",
     "Excitel ब्रॉडबैंड के लिए स्वतंत्र स्पीड टेस्ट। डाउनलोड, अपलोड, पिंग और बफरब्लोट मापें और अपने 200, 300 या 400 Mbps प्लान से तुलना करें — शाम की गिरावट भी पकड़ें।",
     "Excitel स्पीड टेस्ट", "दिल्ली NCR, हैदराबाद, बेंगलुरु और दूसरे शहरों के Excitel यूज़र्स के लिए। टेस्ट चलाएँ, अपना प्लान डालें और देखें कि कितना प्रतिशत मिल रहा है — फिर रात 9 बजे दोबारा चलाकर दिन के नंबर से तुलना करें।",
     [("Excitel में कितनी स्पीड मिलनी चाहिए?", "Excitel के लोकप्रिय प्लान 200, 300 और 400 Mbps हैं और आमतौर पर अपलोड भी इतना ही होता है। LAN पर प्लान का 85–95% सामान्य है, यानी 300 Mbps पर 255–285 Mbps। Wi‑Fi पर पुराने फ़ोन 2.4 GHz बैंड में 50–70 Mbps से ऊपर नहीं जाते, इसलिए 5 GHz नेटवर्क पर टेस्ट करें।"),
      ("Excitel रात को धीमा क्यों हो जाता है?", "Excitel कई इलाकों में लोकल केबल ऑपरेटर (LCO) के ज़रिए बिल्डिंग तक पहुँचता है, और एक स्विच पर कई घर होने से 8–11 बजे भीड़ आम है। दोपहर में 280 Mbps और रात में 60 Mbps मिले तो यह आपका राउटर नहीं, लोकल नेटवर्क की भीड़ है। यहाँ मॉनिटर मोड से 2–3 दिन का लॉग रखें और CSV के साथ Excitel ऐप में शिकायत करें।"),
      ("Excitel पर पिंग और गेमिंग कैसा रहता है?", "Excitel के ज़्यादातर शहरों में Cloudflare का डेटा सेंटर पास है, इसलिए LAN पर 5–20 ms पिंग मिलना चाहिए। गेमिंग में लैग आए तो इस पेज का बफरब्लोट ग्रेड देखें — C या खराब हो तो राउटर में QoS चालू करें। 50 ms से ऊपर का पिंग शांत समय में भी आए तो बिल्डिंग के स्विच या LCO लिंक में दिक्कत है।"),
      ("क्या यह Excitel का आधिकारिक टेस्ट है?", "नहीं। gbps.run स्वतंत्र है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="excitel-speed-test")
page("hi", "free-fire-ping-test", "Free Fire पिंग", "Free Fire पिंग टेस्ट – मोबाइल पर लैग ठीक करें | gbps.run",
     "ब्राउज़र में Free Fire पिंग टेस्ट: पिंग, जिटर, पैकेट लॉस और लोड के साथ पिंग मापें, और Jio, Airtel या Vi पर लैग घटाने के आसान तरीके जानें — कोई ऐप नहीं।",
     "Free Fire पिंग टेस्ट", "Free Fire में हेडशॉट मिस होना या दुश्मन का अचानक दिखना ज़्यादातर ऊँचे पिंग और जिटर की वजह से होता है, स्पीड की वजह से नहीं। पहले Wi‑Fi पर टेस्ट करें, फिर मोबाइल डेटा पर — जिसमें पिंग और जिटर कम आए, मैच उसी पर खेलें।",
     [("Free Fire के लिए अच्छा पिंग कितना है?", "50 ms से कम बेहतरीन है, 50–100 ms में खेलने में कोई दिक्कत नहीं, और 150 ms से ऊपर लैग साफ़ महसूस होता है। जिटर पिंग जितना ही ज़रूरी है — 15 ms से कम रहे तो मूवमेंट और गोली एक-सी चलती है; 30 ms से ऊपर जिटर में पिंग अच्छा होकर भी गेम 'रबर-बैंड' करता है।"),
      ("Free Fire मोबाइल डेटा पर खेलूँ या Wi‑Fi पर?", "जिस पर यहाँ जिटर कम आए। Jio या Airtel 5G पर अक्सर 20–40 ms पिंग मिलता है जो भीड़ वाले घर के Wi‑Fi से बेहतर है; वहीं राउटर के पास 5 GHz Wi‑Fi आमतौर पर 4G को हरा देता है। 2.4 GHz Wi‑Fi से हमेशा बचें — पड़ोसियों के नेटवर्क से टकराव जिटर बढ़ाता है।"),
      ("Free Fire का लैग कैसे कम करें?", "बैकग्राउंड ऐप और डाउनलोड बंद करें (YouTube, अपडेट, WhatsApp बैकअप), फ़ोन को 5 GHz नेटवर्क से जोड़ें, गेम सेटिंग में India सर्वर चुनें, और अगर इस पेज पर बफरब्लोट ग्रेड C या खराब है तो राउटर में QoS/गेमिंग मोड चालू करें। मोबाइल डेटा पर खिड़की के पास बैठने से भी पिंग 20–30 ms तक घट सकता है।"),
      ("क्या यह Free Fire सर्वर तक का पिंग है?", "नहीं — यह भारत में नज़दीकी Cloudflare डेटा सेंटर तक है, जो आपके कनेक्शन की बेसलाइन बताता है। Free Fire के India सर्वर इसके ऊपर 10–30 ms जोड़ते हैं, इसलिए यहाँ 40 ms आए तो गेम में 50–70 ms दिखना सामान्य है।")], alt="free-fire-ping-test")
page("hi", "is-jio-down", "क्या Jio डाउन है?", "क्या Jio डाउन है? अभी लाइव कनेक्शन चेक करें | gbps.run",
     "सेकंडों में जानें कि Jio सिर्फ़ आपके लिए बंद है या सबके लिए। लाइव कनेक्टिविटी चेक, फिर पूरा स्पीड टेस्ट — ताकि आउटेज, भीड़ और धीमे Wi‑Fi का फ़र्क पता चले।",
     "क्या Jio अभी डाउन है?", "यह पेज खुलते ही आपका कनेक्शन अपने-आप जाँचता है। अगर कनेक्शन चालू दिखे पर सब धीमा लगे, तो नीचे पूरा टेस्ट चलाएँ — आउटेज और धीमे Wi‑Fi का फ़र्क उसी से पता चलता है। आधिकारिक स्टेटस: MyJio ऐप / jio.com।",
     [("कैसे पता करें कि Jio डाउन है या सिर्फ़ मेरा कनेक्शन?", "पहले देखें कि घर के दूसरे डिवाइस (दूसरा फ़ोन, टीवी) भी ऑफ़लाइन हैं या नहीं। JioFiber पर ONT की LOS लाइट लाल जले तो फ़ाइबर लाइन में दिक्कत है; PON हरी और इंटरनेट फिर भी बंद हो तो ONT और राउटर 30 सेकंड अनप्लग करके रीस्टार्ट करें। मोबाइल पर एक बार फ़्लाइट मोड ऑन-ऑफ़ करें। फिर भी बंद हो तो MyJio ऐप में सर्विस स्टेटस देखें और पड़ोसियों से पूछें — इलाके का आउटेज आमतौर पर एक साथ कई घरों में दिखता है।"),
      ("Jio आउटेज के दौरान क्या करें?", "ज़रूरी काम के लिए दूसरे नेटवर्क के फ़ोन का हॉटस्पॉट इस्तेमाल करें (घर में Airtel या Vi का सिम हो तो बढ़िया)। ONT/राउटर को चालू रहने दें ताकि सर्विस लौटते ही अपने-आप जुड़ जाए। आउटेज का समय नोट कर लें — लंबे आउटेज पर MyJio ऐप से शिकायत करने पर क्रेडिट या प्लान एक्सटेंशन मिल सकता है।"),
      ("ऊपर 'कनेक्शन चालू' दिखा रहा है पर सब कुछ धीमा है", "तो यह आउटेज नहीं है। नीचे पूरा टेस्ट चलाएँ: डाउनलोड कम और पिंग 100 ms से ऊपर हो तो पीक-ऑवर की भीड़ या Wi‑Fi की समस्या है; पैकेट लॉस 1% से ऊपर हो तो लाइन या टावर की दिक्कत है। Jio AirFiber और Jio 5G पर शाम 8–11 बजे स्पीड गिरना आम है — मॉनिटर मोड से पूरे दिन का लॉग रखें।"),
      ("क्या यह Jio से जुड़ा हुआ है?", "नहीं। gbps.run स्वतंत्र है, विज्ञापन-मुक्त है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="is-jio-down", mode="outage")
page("hi", "is-airtel-down", "क्या Airtel डाउन है?", "क्या Airtel डाउन है? अभी लाइव कनेक्शन चेक करें | gbps.run",
     "सेकंडों में जानें कि Airtel सिर्फ़ आपके लिए बंद है या पूरे इलाके में। लाइव कनेक्टिविटी चेक, फिर पूरा स्पीड टेस्ट — आउटेज, भीड़ और धीमे Wi‑Fi का फ़र्क पता चले।",
     "क्या Airtel अभी डाउन है?", "यह पेज खुलते ही आपका कनेक्शन जाँच लेता है — Airtel Xstream Fiber, Airtel 4G/5G या Airtel हॉटस्पॉट, तीनों पर काम करता है। कनेक्शन चालू दिखे पर सब कुछ अटक रहा हो, तो नीचे पूरा टेस्ट चलाएँ: आउटेज और भीड़/Wi‑Fi की समस्या का फ़र्क उसी से पता चलता है। आधिकारिक स्टेटस: Airtel Thanks ऐप।",
     [("कैसे जानें कि Airtel डाउन है या सिर्फ़ मेरे यहाँ?", "सबसे पहले देखें कि घर के बाकी डिवाइस भी ऑफ़लाइन हैं या नहीं। Airtel Xstream Fiber पर ONT की LOS लाइट लाल जले तो फ़ाइबर केबल में कट या इलाके की लाइन में खराबी है; लाइट सब हरी हों और इंटरनेट फिर भी न चले तो ONT और राउटर दोनों 30 सेकंड अनप्लग करके फिर से चालू करें। मोबाइल पर सिग्नल बार दिखें पर डेटा न चले, तो एक बार फ़्लाइट मोड ऑन-ऑफ़ करें और APN में airtelgprs.com चुना हो यह देखें। इसके बाद भी बंद हो तो Airtel Thanks ऐप में Help सेक्शन देखें — वहाँ इलाके के आउटेज अक्सर पहले से दिखते हैं।"),
      ("Airtel आउटेज के दौरान क्या करें?", "ज़रूरी काम के लिए घर में Jio या Vi सिम वाले फ़ोन का हॉटस्पॉट इस्तेमाल करें। ONT और राउटर को चालू ही रहने दें ताकि सर्विस लौटते ही अपने-आप जुड़ जाएँ — बार-बार रीस्टार्ट करने से कुछ नहीं बदलता। आउटेज का शुरू और ख़त्म होने का समय नोट करें; Xstream Fiber पर 121 या Airtel Thanks ऐप से शिकायत दर्ज करने पर कई बार दिनों के हिसाब से प्लान क्रेडिट मिल जाता है।"),
      ("ऊपर 'कनेक्शन चालू' दिखा रहा है पर Airtel बहुत धीमा है", "तो यह आउटेज नहीं है। नीचे पूरा टेस्ट चलाएँ और नतीजे पढ़ें: डाउनलोड प्लान से बहुत कम और पिंग 100 ms से ऊपर हो तो शाम की भीड़ या Wi‑Fi की समस्या है; पैकेट लॉस 1% से ऊपर हो तो फ़ाइबर लाइन या टावर में दिक्कत है। Airtel 5G पर घर के अंदर स्पीड अचानक 4G जैसी हो जाना आम है — खिड़की के पास टेस्ट करके देखें। Xstream Fiber पर रात 8–11 बजे की गिरावट पकड़ने के लिए मॉनिटर मोड चालू रखें।"),
      ("क्या यह Airtel से जुड़ा हुआ है?", "नहीं। gbps.run स्वतंत्र है, विज्ञापन-मुक्त है और किसी प्रोवाइडर से जुड़ा नहीं है।")], alt="is-airtel-down", mode="outage")

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
        "{{PLAN_PRESET}}": str(p["plan"] or 0), "{{MODE}}": p["mode"], "{{L_JSON}}": json.dumps(S, ensure_ascii=False), "{{ANALYTICS}}": ANALYTICS["gbps.run"], "{{BACKENDS}}": json.dumps(BACKENDS), "{{BACKEND0}}": BACKENDS[0],
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
    html_out = render(LIVE_PAGE).replace(ANALYTICS["gbps.run"], ANALYTICS["gbps.live"])
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
    open(os.path.join(out, "5e7b003d7a8edabb44f639805da74ce8.txt"), "w").write("5e7b003d7a8edabb44f639805da74ce8")
    print(f"built gbps.live → {out}/")

BADGE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="180" height="36" viewBox="0 0 180 36" role="img" aria-label="Test your speed on gbps.run"><rect width="180" height="36" rx="8" fill="#0b1220"/><rect x="0.5" y="0.5" width="179" height="35" rx="7.5" fill="none" stroke="#22d3ee" stroke-opacity=".5"/><circle cx="18" cy="18" r="6" fill="#22d3ee"/><text x="32" y="15" font-family="system-ui,Segoe UI,Roboto,sans-serif" font-size="10" fill="#94a3b8">SPEED TEST</text><text x="32" y="28" font-family="system-ui,Segoe UI,Roboto,sans-serif" font-size="13" font-weight="700" fill="#f8fafc">gbps.run</text><text x="170" y="23" text-anchor="end" font-family="system-ui,Segoe UI,Roboto,sans-serif" font-size="11" fill="#22d3ee">test →</text></svg>"""

def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT); urls = []
    for p in P:
        d = os.path.join(OUT, path_of(p).strip("/")); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(render(p))
        urls.append((url_of(p), "1.0" if not p["slug"] else ("0.8" if p["mode"] == "test" else "0.7")))
    open(os.path.join(OUT, "badge.svg"), "w", encoding="utf-8").write(BADGE_SVG)
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
    open(os.path.join(OUT, "5e7b003d7a8edabb44f639805da74ce8.txt"), "w").write("5e7b003d7a8edabb44f639805da74ce8")  # IndexNow key (Bing/Yandex instant indexing)
    print(f"built {len(urls)} pages → {OUT}/")
    build_live()

if __name__ == "__main__":
    main()
