#!/usr/bin/env python3

# Auto-instalación de dependencias si no están disponibles
try:
    import discord
except ImportError:
    print("📦 discord.py no encontrado. Instalando automáticamente...")
    import subprocess
    import sys

    # Intentar instalar discord.py
    install_methods = [
        [sys.executable, "-m", "pip", "install", "discord.py"],
        [sys.executable, "-m", "pip", "install", "--user", "discord.py"],
        ["pip3", "install", "discord.py"],
        [sys.executable, "-m", "pip", "install", "--break-system-packages", "discord.py"],
    ]

    installed = False
    for method in install_methods:
        try:
            result = subprocess.run(method, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(f"✅ discord.py instalado con: {' '.join(method)}")
                installed = True
                break
        except:
            continue

    if not installed:
        print("❌ No se pudo instalar discord.py automáticamente")
        print("🔧 Instala manualmente con: pip install discord.py")
        exit(1)

    # Intentar importar después de la instalación
    try:
        import discord
        print("✅ discord.py importado correctamente")
    except ImportError:
        print("❌ Error: discord.py instalado pero no se puede importar")
        print("🔧 Reinicia el bot o instala manualmente")
        exit(1)

from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
import asyncio
import pytz
from zoneinfo import ZoneInfo

from time_tracker import TimeTracker

# Configuración del bot
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
time_tracker = TimeTracker()

# Variables para IDs de canales de notificación
NOTIFICATION_CHANNEL_ID = 1382195219939852479
PAUSE_NOTIFICATION_CHANNEL_ID = 1382194854078971975
CANCELLATION_NOTIFICATION_CHANNEL_ID = 1382194963986649219
MOVEMENTS_CHANNEL_ID = 1382193854299504761  # Canal para notificaciones de movimientos

# Configuración de zona horaria México
MEXICO_TZ = ZoneInfo("America/Mexico_City")
START_TIME_HOUR = 19  # 7 PM
START_TIME_MINUTE = 00  # 00 minutos

# Task para verificar hora de inicio
auto_start_task = None
auto_stop_task = None

# Cargar configuración completa desde config.json
config = {}
GOLD_ROLE_ID = 1382198935971430440  # ID Gold hardcoded
RECLUTA_ROLE_ID = 1366550916752216222  # ID Recluta hardcoded

try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Usar el ID del config si existe, sino usar el hardcoded
    config_gold_id = config.get('gold_role_id')
    if config_gold_id:
        GOLD_ROLE_ID = config_gold_id

    print(f"✅ Rol Gold configurado: ID {GOLD_ROLE_ID}")
    print(f"✅ Rol Recluta configurado: ID {RECLUTA_ROLE_ID}")

    # Cargar IDs de canales de notificación desde config
    notification_channels = config.get('notification_channels', {})
    NOTIFICATION_CHANNEL_ID = notification_channels.get('milestones', 1385005232685318281)
    PAUSE_NOTIFICATION_CHANNEL_ID = notification_channels.get('pauses', 1385005232685318282)
    CANCELLATION_NOTIFICATION_CHANNEL_ID = notification_channels.get('cancellations', 1385005232685318284)
    MOVEMENTS_CHANNEL_ID = notification_channels.get('movements', 1385005232685318277)

    print(f"✅ Canales de notificación cargados:")
    print(f"  - Milestones: {NOTIFICATION_CHANNEL_ID}")
    print(f"  - Pausas: {PAUSE_NOTIFICATION_CHANNEL_ID}")
    print(f"  - Cancelaciones: {CANCELLATION_NOTIFICATION_CHANNEL_ID}")
    print(f"  - Movimientos: {MOVEMENTS_CHANNEL_ID}")

except Exception as e:
    print(f"⚠️ No se pudo cargar configuración: {e}")
    config = {}
    # Valores por defecto si no se puede cargar config
    NOTIFICATION_CHANNEL_ID = 1385005232685318281
    PAUSE_NOTIFICATION_CHANNEL_ID = 1385005232685318282
    CANCELLATION_NOTIFICATION_CHANNEL_ID = 1385005232685318284
    MOVEMENTS_CHANNEL_ID = 1385005232685318277
    GOLD_ROLE_ID = 1382198935971430440
    RECLUTA_ROLE_ID = 1366550916752216222

# Task para verificar milestones periódicamente
milestone_check_task = None

@bot.event
async def on_ready():
    print(f'{bot.user} se ha conectado a Discord!')

    # Verificar que el canal de notificaciones existe
    channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
    if channel:
        if hasattr(channel, 'name'):
            print(f'Canal de notificaciones encontrado: {channel.name} (ID: {channel.id})')
        else:
            print(f'Canal de notificaciones encontrado (ID: {channel.id})')
    else:
        print(f'⚠️ Canal de notificaciones no encontrado con ID: {NOTIFICATION_CHANNEL_ID}')

    try:
        # Sincronización global primero
        print("🔄 Sincronizando comandos globalmente...")
        synced_global = await bot.tree.sync()
        print(f'✅ Sincronizados {len(synced_global)} comando(s) slash globalmente')

        # Sincronización específica del guild si hay guilds
        if bot.guilds:
            for guild in bot.guilds:
                try:
                    print(f"🔄 Sincronizando comandos en {guild.name} (ID: {guild.id})...")
                    synced_guild = await bot.tree.sync(guild=guild)
                    print(f'✅ Sincronizados {len(synced_guild)} comando(s) en {guild.name}')
                except Exception as guild_error:
                    print(f'⚠️ Error sincronizando en {guild.name}: {guild_error}')

        # Listar todos los comandos registrados
        commands = [cmd.name for cmd in bot.tree.get_commands()]
        print(f'📋 Comandos registrados ({len(commands)}): {", ".join(commands)}')

        print("💡 Si los comandos no aparecen inmediatamente:")
        print("   • Espera 1-5 minutos para que Discord los propague")
        print("   • Reinicia tu cliente de Discord")
        print("   • Verifica que el bot tenga permisos de 'applications.commands'")

    except Exception as e:
        print(f'❌ Error al sincronizar comandos: {e}')

def is_admin():
    """Decorator para verificar si el usuario tiene permisos"""
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            if not hasattr(interaction, 'guild') or not interaction.guild:
                return False

            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                return False

            if member.bot:
                return False

            return True

        except Exception as e:
            print(f"Error en verificación de permisos para {interaction.user.display_name}: {e}")
            return False

    return discord.app_commands.check(predicate)

def load_config():
    """Cargar configuración desde config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        return {}



def calculate_credits(total_seconds: float, role_type: str = "normal") -> int:
    """Calcular créditos basado en el tiempo total y el rol - SISTEMA SIMPLIFICADO"""
    try:
        if not isinstance(total_seconds, (int, float)) or total_seconds < 0:
            return 0

        total_hours = total_seconds / 3600

        if role_type == "gold":
            if total_hours >= 2.0:
                return 10  # 2 horas = 10 créditos
            elif total_hours >= 1.0:
                return 5   # 1 hora = 5 créditos
            else:
                return 0   # Menos de 1 hora = 0 créditos
        else:
            # Usuarios sin rol específico (normal)
            if total_hours >= 1.0:
                return 3   # 1 hora = 3 créditos
            else:
                return 0   # Menos de 1 hora = 0 créditos

    except Exception as e:
        print(f"Error calculando créditos: {e}")
        return 0

def get_user_role_type(member: discord.Member) -> str:
    """Determina el tipo de rol del usuario - SISTEMA SIMPLIFICADO"""
    if not member:
        return "normal"

    # Verificar Gold por ID específico (prioritario)
    gold_role_ids = [GOLD_ROLE_ID, 1382198935971430440]  # Config + hardcoded

    for role in member.roles:
        # Verificar si tiene rol Gold por ID
        if role.id in gold_role_ids:
            return "gold"
        # También verificar por nombre que contenga "gold" (case insensitive)
        if "gold" in role.name.lower():
            return "gold"

    return "normal"

def get_role_info(member: discord.Member) -> str:
    """Obtiene la información del rol simplificada del usuario"""
    if not member:
        return " (Recluta)"

    # Verificar si es Gold con más detalle
    role_type = get_user_role_type(member)
    if role_type == "gold":
        # Encontrar el nombre específico del rol Gold
        gold_role_ids = [GOLD_ROLE_ID, 1382198935971430440]
        for role in member.roles:
            if role.id in gold_role_ids or "gold" in role.name.lower():
                return f" (Gold - {role.name})"
        return " (Gold)"
    else:
        return " (Recluta)"

def has_unlimited_time_role(member: discord.Member) -> bool:
    """Verificar si el usuario tiene un rol que le otorga tiempo ilimitado (rol Gold)"""
    if not member:
        return False

    # En este sistema, el rol Gold otorga "tiempo ilimitado" (2 horas en lugar de 1)
    role_type = get_user_role_type(member)
    return role_type == "gold"

@bot.tree.command(name="iniciar_tiempo", description="Iniciar el seguimiento de tiempo para un usuario")
@discord.app_commands.describe(usuario="El usuario para quien iniciar el seguimiento de tiempo")
@is_admin()
async def iniciar_tiempo(interaction: discord.Interaction, usuario: discord.Member):
    if usuario.bot:
        await interaction.response.send_message("❌ No se puede rastrear el tiempo de bots.", ephemeral=True)
        return

    # Verificar que el usuario tenga el rol requerido (ID: 1366550916752216221)
    required_role_id = 1366550916752216221
    has_required_role = any(role.id == required_role_id for role in usuario.roles)

    if not has_required_role:
        await interaction.response.send_message(
            f"❌ {usuario.mention} no tiene el rol requerido para iniciar tiempo. "
            f"Se requiere el rol de Verificado.",
            ephemeral=True
        )
        return

    # Obtener hora actual en México
    mexico_now = datetime.now(MEXICO_TZ)
    current_hour = mexico_now.hour
    current_minute = mexico_now.minute
    
    # NUEVA VALIDACIÓN: No permitir iniciar después de las 20:20 (8:20 PM)
    cutoff_hour = 20
    cutoff_minute = 20
    is_after_cutoff = (current_hour > cutoff_hour) or (current_hour == cutoff_hour and current_minute >= cutoff_minute)
    
    if is_after_cutoff:
        await interaction.response.send_message(
            f"❌ No se pueden iniciar tiempos después de las 20:20 (9:25 PM) hora México.\n"
            f"⏰ Hora actual: {mexico_now.strftime('%H:%M')} México",
            ephemeral=True
        )
        return

    role_type = get_user_role_type(usuario)

    # Verificar si el usuario ya ha completado sus horas máximas
    user_data = time_tracker.get_user_data(usuario.id)
    if user_data:
        total_time = time_tracker.get_total_time(usuario.id)
        total_hours = total_time / 3600

        # Verificar límites según el tipo de rol
        if user_data.get("milestone_completed", False):
            await interaction.response.send_message(
                f"❌ {usuario.mention} ya ha completado su tiempo máximo y no puede iniciar tiempo nuevamente."
            )
            return
        elif role_type == "gold" and total_hours >= 2.0:
            await interaction.response.send_message(
                f"❌ {usuario.mention} ya ha completado sus 2 horas máximas (Gold) y no puede iniciar tiempo nuevamente."
            )
            return
        elif role_type == "normal" and total_hours >= 1.0:
            await interaction.response.send_message(
                f"❌ {usuario.mention} ya ha completado su 1 hora máxima (Recluta) y no puede iniciar tiempo nuevamente."
            )
            return

    # Verificar si el usuario tiene tiempo pausado
    if user_data and user_data.get('is_paused', False):
        await interaction.response.send_message(
            f"⚠️ {usuario.mention} tiene tiempo pausado. Usa `/despausar_tiempo` para continuar el tiempo."
        )
        return

    # Verificar si es antes de la hora configurada (19:00)
    is_before_start_time = (current_hour < START_TIME_HOUR) or (current_hour == START_TIME_HOUR and current_minute < START_TIME_MINUTE)

    if is_before_start_time:
        # Pre-registro: registrar usuario pero no iniciar cronómetro
        success = time_tracker.pre_register_user(usuario.id, usuario.display_name)
        if success:
            # Guardar quién hizo el pre-registro
            time_tracker.set_pre_register_initiator(usuario.id, interaction.user.id, interaction.user.display_name)
            await interaction.response.send_message(
                f"📝 El tiempo de {usuario.mention} ha sido registrado por {interaction.user.mention}"
            )
        else:
            await interaction.response.send_message(f"⚠️ {usuario.mention} ya está pre-registrado", ephemeral=True)
    else:
        # Hora configurada o después: iniciar normally
        success = time_tracker.start_tracking(usuario.id, usuario.display_name)
        if success:
            await interaction.response.send_message(f"⏰ El tiempo de {usuario.mention} ha sido iniciado por {interaction.user.mention}")
        else:
            await interaction.response.send_message(f"⚠️ El tiempo de {usuario.mention} ya está activo", ephemeral=True)

@bot.tree.command(name="pausar_tiempo", description="Pausar el tiempo de un usuario")
@discord.app_commands.describe(usuario="El usuario para quien pausar el tiempo")
@is_admin()
async def pausar_tiempo(interaction: discord.Interaction, usuario: discord.Member):
    user_data = time_tracker.get_user_data(usuario.id)
    total_time_before = time_tracker.get_total_time(usuario.id)

    # Obtener el tipo de rol del usuario para pasarlo a pause_tracking
    role_type = get_user_role_type(usuario)
    success = time_tracker.pause_tracking(usuario.id, user_role_type=role_type) # Pasar el tipo de rol

    if success:
        # Obtener el tiempo total después de pausar para la notificación
        total_time_after = time_tracker.get_total_time(usuario.id)
        session_time = total_time_after - total_time_before
        pause_count = time_tracker.get_pause_count(usuario.id) # Obtener el nuevo contador de pausas

        formatted_total_time = time_tracker.format_time_human(total_time_after)
        formatted_session_time = time_tracker.format_time_human(session_time) if session_time > 0 else "0 Segundos"

        # Verificar si el usuario fue cancelado automáticamente por llegar a 3 pausas
        user_data_updated = time_tracker.get_user_data(usuario.id)
        was_auto_cancelled = (user_data_updated and
                             user_data_updated.get('pause_count', 0) == 0 and
                             not user_data_updated.get('is_paused', False) and
                             not user_data_updated.get('is_active', False) and
                             role_type != "gold")

        if was_auto_cancelled:
            # Usuario cancelado automáticamente por 3 pausas
            time_lost = user_data.get('time_lost_on_cancellation', 0) if user_data else 0
            formatted_time_lost = time_tracker.format_time_human(time_lost) if time_lost > 0 else "0 Segundos"

            await interaction.response.send_message(
                f"🚫 **{usuario.mention} ha alcanzado el límite de 3 pausas y su tiempo ha sido cancelado automáticamente.**\n"
                f"🕐 **Tiempo conservado:** {formatted_total_time} (solo horas completas)\n"
                f"❌ **Tiempo perdido:** {formatted_time_lost}"
            )

            # Enviar notificación SOLO al canal de cancelaciones (NO al de pausas)
            await send_auto_cancellation_notification(usuario.display_name, formatted_total_time, interaction.user.mention, 3, time_lost)
        else:
            # Pausa normal (usuarios Gold o pausas 1/3, 2/3 para reclutas)
            await interaction.response.send_message(f"⏸️ El tiempo de {usuario.mention} ha sido pausado")

            # Enviar notificación al canal de pausas SOLO si NO fue cancelado automáticamente
            await send_pause_notification(usuario.display_name, total_time_after, interaction.user.mention, formatted_session_time, pause_count, role_type)
    else:
        await interaction.response.send_message(f"⚠️ No hay tiempo activo para {usuario.mention}", ephemeral=True)

@bot.tree.command(name="despausar_tiempo", description="Despausar el tiempo de un usuario")
@discord.app_commands.describe(usuario="El usuario para quien despausar el tiempo")
@is_admin()
async def despausar_tiempo(interaction: discord.Interaction, usuario: discord.Member):
    paused_duration = time_tracker.get_paused_duration(usuario.id)
    success = time_tracker.resume_tracking(usuario.id)
    if success:
        total_time = time_tracker.get_total_time(usuario.id)
        formatted_paused_duration = time_tracker.format_time_human(paused_duration) if paused_duration > 0 else "0 Segundos"
        await interaction.response.send_message(
            f"▶️ El tiempo de {usuario.mention} ha sido despausado"
        )
        await send_unpause_notification(usuario.display_name, total_time, interaction.user.mention, formatted_paused_duration)
    else:
        await interaction.response.send_message(f"⚠️ No se puede despausar - {usuario.mention} no tiene tiempo pausado", ephemeral=True)

@bot.tree.command(name="sumar_minutos", description="Sumar minutos al tiempo de un usuario")
@discord.app_commands.describe(
    usuario="El usuario al que sumar tiempo",
    minutos="Cantidad de minutos a sumar"
)
@is_admin()
async def sumar_minutos(interaction: discord.Interaction, usuario: discord.Member, minutos: int):
    if minutos <= 0:
        await interaction.response.send_message("❌ La cantidad de minutos debe ser positiva", ephemeral=True)
        return

    success = time_tracker.add_minutes(usuario.id, usuario.display_name, minutos)
    if success:
        total_time = time_tracker.get_total_time(usuario.id)
        formatted_time = time_tracker.format_time_human(total_time)
        await interaction.response.send_message(
            f"✅ Sumados {minutos} minutos a {usuario.mention} por {interaction.user.mention}\n"
            f"⏱️ Tiempo total: {formatted_time}"
        )
        await check_time_milestone(usuario.id, usuario.display_name)
    else:
        await interaction.response.send_message(f"❌ Error al sumar tiempo para {usuario.mention}", ephemeral=True)

@bot.tree.command(name="restar_minutos", description="Restar minutos del tiempo de un usuario")
@discord.app_commands.describe(
    usuario="El usuario al que restar tiempo",
    minutos="Cantidad de minutos a restar"
)
@is_admin()
async def restar_minutos(interaction: discord.Interaction, usuario: discord.Member, minutos: int):
    if minutos <= 0:
        await interaction.response.send_message("❌ La cantidad de minutos debe ser positiva", ephemeral=True)
        return

    success = time_tracker.subtract_minutes(usuario.id, minutos)
    if success:
        total_time = time_tracker.get_total_time(usuario.id)
        formatted_time = time_tracker.format_time_human(total_time)
        await interaction.response.send_message(
            f"➖ Restados {minutos} minutos de {usuario.mention} por {interaction.user.mention}\n"
            f"⏱️ Tiempo total: {formatted_time}"
        )
    else:
        await interaction.response.send_message(f"❌ Error al restar tiempo para {usuario.mention}", ephemeral=True)

# Clase para manejar la paginación
class TimesView(discord.ui.View):
    def __init__(self, sorted_users, guild, max_per_page=20, search_term=None, filter_status=None):
        super().__init__(timeout=300)
        self.sorted_users = sorted_users
        self.guild = guild
        self.max_per_page = max_per_page
        self.current_page = 0
        self.total_pages = (len(sorted_users) + max_per_page - 1) // max_per_page if sorted_users else 1
        self.search_term = search_term
        self.filter_status = filter_status

        # Actualizar estado inicial de botones
        self.update_buttons()

    def get_embed(self):
        """Crear embed para la página actual"""
        start_idx = self.current_page * self.max_per_page
        end_idx = min(start_idx + self.max_per_page, len(self.sorted_users))
        current_users = self.sorted_users[start_idx:end_idx]
        user_list = []

        for _, user_id, data in current_users:
            try:
                user_id_int = int(user_id)
                member = self.guild.get_member(user_id_int) if self.guild else None

                if member:
                    user_mention = member.mention
                    role_type = get_user_role_type(member)
                else:
                    user_name = data.get('name', f'Usuario {user_id}')
                    user_mention = f"**{user_name}** `(ID: {user_id})`"
                    role_type = "normal"

                total_time = time_tracker.get_total_time(user_id_int)
                formatted_time = time_tracker.format_time_human(total_time)

                # Determinar estado del usuario
                total_hours = total_time / 3600
                role_type = get_user_role_type(member) if member else "normal"

                # Verificar si ha completado su tiempo máximo
                is_finished = (data.get("milestone_completed", False) or
                             (role_type == "gold" and total_hours >= 2.0) or
                             (role_type == "normal" and total_hours >= 1.0))

                if data.get('is_active', False):
                    status = "🟢 Activo"
                elif is_finished:
                    status = "✅ Terminado"
                elif data.get('is_paused', False):
                    status = "⏸️ Pausado"
                else:
                    status = "🔴 Inactivo"

                credits = calculate_credits(total_time, role_type)
                credit_info = f" 💰 {credits} Créditos" if credits > 0 else ""
                role_info = get_role_info(member) if member else ""
                user_list.append(f"📌 {user_mention}{role_info} - ⏱️ {formatted_time}{credit_info} {status}")

            except Exception as e:
                print(f"Error procesando usuario {user_id}: {e}")
                continue

        # Título con información de búsqueda y filtros
        title = "⏰ Tiempos Registrados"
        if self.search_term:
            title += f" (Búsqueda: '{self.search_term}')"
        if self.filter_status:
            title += f" (Filtro: {self.filter_status})"

        embed = discord.Embed(
            title=title,
            description="\n".join(user_list) if user_list else "No hay usuarios en esta página",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        footer_text = f"Página {self.current_page + 1}/{self.total_pages} • Total: {len(self.sorted_users)} usuarios"
        if self.search_term:
            footer_text += f" encontrados"

        embed.set_footer(text=footer_text)
        return embed

    @discord.ui.button(label='◀️ Anterior', style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='▶️ Siguiente', style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='📄 Ir a página', style=discord.ButtonStyle.primary)
    async def go_to_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PageModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🔍 Buscar', style=discord.ButtonStyle.secondary)
    async def search_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SearchModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🔄 Actualizar', style=discord.ButtonStyle.success)
    async def refresh_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()

            # Recargar datos con timeout extendido para muchos usuarios
            tracked_users = await asyncio.wait_for(
                asyncio.to_thread(time_tracker.get_all_tracked_users),
                timeout=15.0
            )

            # Aplicar filtros existentes con timeout
            filtered_users = await asyncio.wait_for(
                self._apply_filters(tracked_users),
                timeout=10.0
            )

            # Actualizar datos internos
            self.sorted_users = filtered_users
            self.total_pages = (len(filtered_users) + self.max_per_page - 1) // self.max_per_page if filtered_users else 1

            # Asegurar que la página actual sea válida
            if self.current_page >= self.total_pages:
                self.current_page = max(0, self.total_pages - 1)

            # Rehabilitar botones de navegación si hay múltiples páginas
            if self.total_pages > 1:
                for item in self.children:
                    if isinstance(item, discord.ui.Button) and item.label in ['◀️ Anterior', '▶️ Siguiente', '📄 Ir a página']:
                        # Rehabilitar botones que podrían haberse deshabilitado incorrectamente
                        if item.label == '📄 Ir a página':
                            item.disabled = False
                        elif item.label == '◀️ Anterior':
                            item.disabled = (self.current_page == 0)
                        elif item.label == '▶️ Siguiente':
                            item.disabled = (self.current_page >= self.total_pages - 1)

            # Actualizar botones
            self.update_buttons()

            # Obtener embed actualizado
            embed = self.get_embed()

            # Actualizar el mensaje existente
            await interaction.edit_original_response(embed=embed, view=self)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(content="⚠️ Timeout al actualizar datos. Intenta de nuevo.")
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error al actualizar: {e}")

    @discord.ui.select(
        placeholder="Filtrar por estado...",
        options=[
            discord.SelectOption(label="Todos los usuarios", value="all", emoji="📋"),
            discord.SelectOption(label="Solo Activos", value="active", emoji="🟢"),
            discord.SelectOption(label="Solo Pausados", value="paused", emoji="⏸️"),
            discord.SelectOption(label="Solo Terminados", value="finished", emoji="✅"),
            discord.SelectOption(label="Solo Inactivos", value="inactive", emoji="🔴")
        ]
    )
    async def filter_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_filter = select.values[0]

        try:
            # Recargar datos
            tracked_users = await asyncio.wait_for(
                asyncio.to_thread(time_tracker.get_all_tracked_users),
                timeout=5.0
            )

            # Aplicar filtro seleccionado
            self.filter_status = selected_filter if selected_filter != "all" else None
            filtered_users = await self._apply_filters(tracked_users)

            # Actualizar datos y resetear página
            self.sorted_users = filtered_users
            self.current_page = 0
            self.total_pages = (len(filtered_users) + self.max_per_page - 1) // self.max_per_page if filtered_users else 1

            # Actualizar botones según nueva paginación
            self.update_buttons()

            # Obtener embed actualizado
            embed = self.get_embed()

            # Actualizar el mensaje existente
            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error aplicando filtro: {e}", ephemeral=True)

    async def _apply_filters(self, tracked_users):
        """Aplicar filtros de búsqueda y estado"""
        filtered_users = []

        for user_id, data in tracked_users.items():
            user_name = data.get('name', f'Usuario {user_id}')

            # Aplicar filtro de búsqueda
            if self.search_term and self.search_term.lower() not in user_name.lower():
                continue

            # Aplicar filtro de estado
            if self.filter_status:
                try:
                    user_id_int = int(user_id)
                    member = self.guild.get_member(user_id_int) if self.guild else None
                    total_time = time_tracker.get_total_time(user_id_int)

                    # Determinar estado actual
                    total_hours = total_time / 3600
                    role_type = get_user_role_type(member) if member else "normal"

                    # Determinar si está terminado (ha alcanzado su límite máximo)
                    is_finished = (data.get("milestone_completed", False) or
                                 (role_type == "gold" and total_hours >= 2.0) or
                                 (role_type == "normal" and total_hours >= 1.0))

                    if data.get('is_active', False):
                        status = "active"
                    elif is_finished:
                        status = "finished"
                    elif data.get('is_paused', False):
                        status = "paused"
                    else:
                        status = "inactive"

                    # Filtrar por estado
                    if self.filter_status != status:
                        continue

                except Exception as e:
                    print(f"Error filtrando usuario {user_id}: {e}")
                    continue

            filtered_users.append((user_name.lower(), user_id, data))

        filtered_users.sort(key=lambda x: x[0])
        return filtered_users

    def update_buttons(self):
        """Actualizar estado de los botones según la página actual"""
        # Buscar los botones de navegación por su label
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == '◀️ Anterior':
                    item.disabled = (self.current_page == 0)
                elif item.label == '▶️ Siguiente':
                    item.disabled = (self.current_page >= self.total_pages - 1)
                elif item.label == '📄 Ir a página':
                    item.disabled = (self.total_pages <= 1)

    async def on_timeout(self):
        """Deshabilitar botones cuando expire el timeout"""
        for item in self.children:
            item.disabled = True

class PageModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title='Ir a Página')
        self.view = view

    page_number = discord.ui.TextInput(
        label='Número de página',
        placeholder=f'Ingresa un número entre 1 y {999}',
        required=True,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page = int(self.page_number.value)
            if 1 <= page <= self.view.total_pages:
                self.view.current_page = page - 1
                self.view.update_buttons()
                embed = self.view.get_embed()
                await interaction.response.edit_message(embed=embed, view=self.view)
            else:
                await interaction.response.send_message(
                    f"❌ Página inválida. Debe estar entre 1 y {self.view.total_pages}",
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message("❌ Por favor ingresa un número válido", ephemeral=True)

class SearchModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title='Buscar Usuario')
        self.view = view

    search_term = discord.ui.TextInput(
        label='Nombre del usuario',
        placeholder='Escribe parte del nombre del usuario...',
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        search_term = self.search_term.value.lower().strip()

        # Obtener todos los usuarios sin filtro
        try:
            tracked_users = await asyncio.wait_for(
                asyncio.to_thread(time_tracker.get_all_tracked_users),
                timeout=2.0
            )

            # Filtrar usuarios
            filtered_users = []
            for user_id, data in tracked_users.items():
                user_name = data.get('name', f'Usuario {user_id}').lower()
                if search_term in user_name:
                    filtered_users.append((user_name, user_id, data))

            filtered_users.sort(key=lambda x: x[0])

            if not filtered_users:
                await interaction.response.send_message(
                    f"❌ No se encontraron usuarios con '{self.search_term.value}' en su nombre",
                    ephemeral=True
                )
                return

            # Crear nueva vista con resultados filtrados
            new_view = TimesView(filtered_users, self.view.guild, max_per_page=self.view.max_per_page,
                               search_term=self.search_term.value, filter_status=self.view.filter_status)
            embed = new_view.get_embed()

            await interaction.response.edit_message(embed=embed, view=new_view)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error en búsqueda: {e}", ephemeral=True)

@bot.tree.command(name="ver_tiempos", description="Ver todos los tiempos registrados con filtros y actualización en tiempo real")
@is_admin()
async def ver_tiempos(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=False)
    except Exception as e:
        print(f"Error al defer la interacción: {e}")
        try:
            await interaction.response.send_message("🔄 Procesando tiempos...", ephemeral=False)
        except Exception:
            return

    try:
        tracked_users = await asyncio.wait_for(
            asyncio.to_thread(time_tracker.get_all_tracked_users),
            timeout=5.0
        )

        if not tracked_users:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("📊 No hay usuarios con tiempo registrado", ephemeral=False)
                else:
                    await interaction.followup.send("📊 No hay usuarios con tiempo registrado")
            except Exception as e:
                print(f"Error enviando mensaje de sin usuarios: {e}")
            return

        # Ordenar usuarios alfabéticamente por nombre
        sorted_users = []
        for user_id, data in tracked_users.items():
            user_name = data.get('name', f'Usuario {user_id}')
            sorted_users.append((user_name.lower(), user_id, data))

        sorted_users.sort(key=lambda x: x[0])

        # Usar paginación con filtrado mejorado y botones de actualización
        view = TimesView(sorted_users, interaction.guild, max_per_page=20)
        embed = view.get_embed()

        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed, view=view)

    except asyncio.TimeoutError:
        error_msg = "❌ Timeout al obtener usuarios. Intenta de nuevo."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(error_msg, ephemeral=False)
            else:
                await interaction.followup.send(error_msg)
        except Exception as e:
            print(f"Error enviando mensaje de timeout: {e}")

    except Exception as e:
        print(f"Error general en ver_tiempos: {e}")
        import traceback
        traceback.print_exc()

        error_msg = "❌ Error interno del comando. Revisa los logs del servidor."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(error_msg, ephemeral=False)
            else:
                await interaction.followup.send(error_msg)
        except Exception as e2:
            print(f"No se pudo enviar mensaje de error final: {e2}")

@bot.tree.command(name="reiniciar_tiempo", description="Reiniciar el tiempo de un usuario a cero")
@discord.app_commands.describe(usuario="El usuario cuyo tiempo se reiniciará")
@is_admin()
async def reiniciar_tiempo(interaction: discord.Interaction, usuario: discord.Member):
    success = time_tracker.reset_user_time(usuario.id)
    if success:
        await interaction.response.send_message(f"🔄 Tiempo reiniciado para {usuario.mention} por {interaction.user.mention}")
    else:
        await interaction.response.send_message(f"❌ No se encontró registro de tiempo para {usuario.mention}", ephemeral=True)

@bot.tree.command(name="reiniciar_todos_tiempos", description="Reiniciar todos los tiempos de todos los usuarios")
@is_admin()
async def reiniciar_todos_tiempos(interaction: discord.Interaction):
    usuarios_reiniciados = time_tracker.reset_all_user_times()
    if usuarios_reiniciados > 0:
        await interaction.response.send_message(f"🔄 Tiempos reiniciados para {usuarios_reiniciados} usuario(s)")
    else:
        await interaction.response.send_message("❌ No hay usuarios con tiempo registrado para reiniciar", ephemeral=True)

@bot.tree.command(name="limpiar_base_datos", description="ELIMINAR COMPLETAMENTE todos los usuarios registrados de la base de datos")
@is_admin()
async def limpiar_base_datos(interaction: discord.Interaction):
    tracked_users = time_tracker.get_all_tracked_users()
    user_count = len(tracked_users)

    if user_count == 0:
        await interaction.response.send_message("❌ No hay usuarios registrados en la base de datos", ephemeral=True)
        return

    embed = discord.Embed(
        title="⚠️ CONFIRMACIÓN REQUERIDA",
        description="Esta acción eliminará COMPLETAMENTE todos los datos de usuarios",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📊 Datos que se eliminarán:",
        value=f"• {user_count} usuarios registrados\n"
              f"• Todo el historial de tiempo\n"
              f"• Sesiones activas\n"
              f"• Contadores de pausas\n"
              f"• Estados de notificaciones\n"
              f"• **TODOS los comandos de pago quedarán vacíos**",
        inline=False
    )
    embed.add_field(
        name="⚠️ ADVERTENCIA:",
        value="Esta acción NO se puede deshacer\n"
              "Los usuarios tendrán que registrarse de nuevo\n"
              "Afecta: `/paga_recluta` y `/paga_gold`",
        inline=False
    )
    embed.add_field(
        name="🔄 Para continuar:",
        value="Usa el comando `/limpiar_base_datos_confirmar` con `confirmar: 'SI'`",
        inline=False
    )
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="limpiar_base_datos_confirmar", description="CONFIRMAR eliminación completa de la base de datos")
@discord.app_commands.describe(confirmar="Escribe 'SI' para confirmar la eliminación completa")
@is_admin()
async def limpiar_base_datos_confirmar(interaction: discord.Interaction, confirmar: str):
    if confirmar.upper() != "SI":
        await interaction.response.send_message("❌ Operación cancelada. Debes escribir 'SI' para confirmar", ephemeral=True)
        return

    tracked_users = time_tracker.get_all_tracked_users()
    user_count = len(tracked_users)

    if user_count == 0:
        await interaction.response.send_message("❌ No hay usuarios registrados en la base de datos", ephemeral=True)
        return

    success = time_tracker.clear_all_data()

    if success:
        embed = discord.Embed(
            title="🗑️ BASE DE DATOS LIMPIADA",
            description="Todos los datos de usuarios han sido eliminados completamente",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="📊 Datos eliminados:",
            value=f"• {user_count} usuarios registrados\n"
                  f"• Todo el historial de tiempo\n"
                  f"• Sesiones activas\n"
                  f"• Archivo user_times.json reiniciado",
            inline=False
        )
        embed.add_field(
            name="✅ Estado actual:",
            value="Base de datos completamente limpia\n"
                  "Sistema listo para nuevos registros",
            inline=False
        )
        embed.set_footer(text=f"Ejecutado por {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Error al limpiar la base de datos", ephemeral=True)

@bot.tree.command(name="cancelar_tiempo", description="Cancelar tiempo del usuario conservando solo horas completas")
@discord.app_commands.describe(usuario="El usuario cuyo tiempo se cancelará (conserva horas completas)")
@is_admin()
async def cancelar_tiempo(interaction: discord.Interaction, usuario: discord.Member):
    user_data = time_tracker.get_user_data(usuario.id)
    total_time = time_tracker.get_total_time(usuario.id)
    user_id = usuario.id

    if user_data:
        # Calcular horas completas y tiempo perdido
        total_hours = int(total_time // 3600)
        hours_time = total_hours * 3600  # Solo horas completas en segundos
        lost_time = total_time - hours_time  # Tiempo perdido (minutos/segundos)

        formatted_total_time = time_tracker.format_time_human(total_time)
        formatted_hours_time = time_tracker.format_time_human(hours_time)
        formatted_lost_time = time_tracker.format_time_human(lost_time)

        # Usar la nueva función de cancelación que conserva horas
        success = time_tracker.cancel_user_tracking_keep_hours(user_id)
        if success:
            if lost_time > 0:
                await interaction.response.send_message(
                    f"🗑️ El tiempo de {usuario.mention} ha sido cancelado\n"
                    f"✅ **Tiempo conservado:** {formatted_hours_time} (horas completas)\n"
                    f"❌ **Tiempo perdido:** {formatted_lost_time}"
                )
                await send_cancellation_notification(usuario.display_name, interaction.user.mention, formatted_total_time, formatted_hours_time, formatted_lost_time)
            else:
                await interaction.response.send_message(
                    f"🗑️ El tiempo de {usuario.mention} ha sido cancelado\n"
                    f"✅ **Tiempo conservado:** {formatted_hours_time}"
                )
                await send_cancellation_notification(usuario.display_name, interaction.user.mention, formatted_total_time, formatted_hours_time)
        else:
            await interaction.response.send_message(f"❌ Error al cancelar el tiempo para {usuario.mention}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ No se encontró registro de tiempo para {usuario.mention}", ephemeral=True)

# Comandos de configuración de canales removidos - ahora se configuran directamente en config.json

@bot.tree.command(name="ver_tiempo", description="Ver estadísticas detalladas de un usuario")
@discord.app_commands.describe(usuario="El usuario del que ver estadísticas")
@is_admin()
async def ver_tiempo(interaction: discord.Interaction, usuario: discord.Member):
    user_data = time_tracker.get_user_data(usuario.id)

    if not user_data:
        await interaction.response.send_message(f"❌ No se encontraron datos para {usuario.mention}", ephemeral=True)
        return

    total_time = time_tracker.get_total_time(usuario.id)
    formatted_time = time_tracker.format_time_human(total_time)

    embed = discord.Embed(
        title=f"📊 Estadísticas de {usuario.display_name}",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )

    embed.add_field(name="⏱️ Tiempo Total", value=formatted_time, inline=True)

    # Determinar estado del usuario
    total_hours = total_time / 3600
    role_type = get_user_role_type(usuario)

    # Verificar si ha completado su tiempo máximo
    is_finished = (user_data.get("milestone_completed", False) or
                  (role_type == "gold" and total_hours >= 2.0) or
                  (role_type == "normal" and total_hours >= 1.0))

    if user_data.get('is_active', False):
        status = "🟢 Activo"
    elif is_finished:
        status = "✅ Terminado"
    elif user_data.get('is_paused', False):
        status = "⏸️ Pausado"
    else:
        status = "🔴 Inactivo"

    embed.add_field(name="📍 Estado", value=status, inline=True)

    # Mostrar tipo de rol del usuario
    role_type = get_user_role_type(usuario)
    if role_type == "gold":
        embed.add_field(name="🎭 Tipo de Usuario", value="🏆 Gold - Límite: 2 horas", inline=True)
    else:
        embed.add_field(name="🎭 Tipo de Usuario", value="👤 Recluta - Límite: 1 hora", inline=True)

    # Mostrar tiempo pausado si aplica
    if user_data.get('is_paused', False):
        paused_duration = time_tracker.get_paused_duration(usuario.id)
        formatted_paused_time = time_tracker.format_time_human(paused_duration) if paused_duration > 0 else "0 Segundos"
        embed.add_field(
            name="⏸️ Tiempo Pausado",
            value=formatted_paused_time,
            inline=False
        )

    # Mostrar contador de pausas
    pause_count = time_tracker.get_pause_count(usuario.id)
    if role_type == "gold":
        embed.add_field(
            name="📊 Pausas",
            value="Ilimitadas (Gold)",
            inline=True
        )
    else:
        pause_text = "pausa" if pause_count == 1 else "pausas"
        embed.add_field(
            name="📊 Pausas",
            value=f"{pause_count} {pause_text} de 3 máximo",
            inline=True
        )

    # Mostrar créditos ganados
    credits = calculate_credits(total_time, role_type)
    embed.add_field(name="💰 Créditos Ganados", value=f"{credits} créditos", inline=True)

    embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else usuario.default_avatar.url)
    embed.set_footer(text="Estadísticas actualizadas")

    await interaction.response.send_message(embed=embed)

# =================== SISTEMA DE ROLES SIMPLIFICADO ===================





@bot.tree.command(name="ver_roles_usuario", description="Ver todos los roles de un usuario")
@discord.app_commands.describe(usuario="El usuario del que ver los roles")
@is_admin()
async def ver_roles_usuario(interaction: discord.Interaction, usuario: discord.Member):
    """Ver todos los roles de un usuario"""
    try:
        user_roles = usuario.roles[1:]  # Excluir @everyone

        if not user_roles:
            await interaction.response.send_message(
                f"📋 {usuario.mention} no tiene roles asignados (excepto @everyone)",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🎭 Roles de {usuario.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else usuario.default_avatar.url)

        # Verificar si tiene rol Gold
        role_type = get_user_role_type(usuario)
        if role_type == "gold":
            gold_roles = [role for role in user_roles if "gold" in role.name.lower()]
            if gold_roles:
                gold_text = ""
                for role in gold_roles:
                    gold_text += f"🏆 **{role.name}**\n"
                embed.add_field(name="⭐ Rol Gold", value=gold_text, inline=False)

        # Otros roles
        other_roles = [role for role in user_roles if "gold" not in role.name.lower()]
        if other_roles:
            otros_text = ""
            for role in other_roles[:10]:  # Limitar a 10 roles
                otros_text += f"• {role.name}\n"
            if len(other_roles) > 10:
                otros_text += f"... y {len(other_roles) - 10} más"
            embed.add_field(name="📋 Otros Roles", value=otros_text, inline=False)

        embed.add_field(name="📊 Total de Roles", value=str(len(user_roles)), inline=True)
        embed.set_footer(text="Información de roles")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message("❌ Error al obtener información de roles.", ephemeral=True)
        print(f"Error obteniendo roles de usuario: {e}")

@bot.tree.command(name="ver_pre_registrados", description="Ver usuarios pre-registrados esperando las 8 PM")
@is_admin()
async def ver_pre_registrados(interaction: discord.Interaction):
    """Mostrar usuarios que están pre-registrados"""
    try:
        pre_registered_users = time_tracker.get_pre_registered_users()

        if not pre_registered_users:
            await interaction.response.send_message("📋 No hay usuarios pre-registrados actualmente", ephemeral=True)
            return

        mexico_now = datetime.now(MEXICO_TZ)

        embed = discord.Embed(
            title="📋 Usuarios Pre-registrados",
            description="Usuarios esperando el inicio automático a las 14:38 México",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        user_list = []
        for user_id_str, data in pre_registered_users.items():
            try:
                user_id = int(user_id_str)
                member = interaction.guild.get_member(user_id) if interaction.guild else None

                if member:
                    user_mention = member.mention
                else:
                    user_name = data.get('name', f'Usuario {user_id}')
                    user_mention = f"**{user_name}** `(ID: {user_id})`"

                pre_register_time = data.get('pre_register_time', '')
                if pre_register_time:
                    try:
                        register_dt = datetime.fromisoformat(pre_register_time)
                        time_str = register_dt.strftime("%H:%M")
                    except:
                        time_str = "N/A"
                else:
                    time_str = "N/A"

                user_list.append(f"📌 {user_mention} - Registrado a las {time_str}")

            except Exception as e:
                print(f"Error procesando usuario pre-registrado {user_id_str}: {e}")
                continue

        if user_list:
            embed.add_field(
                name=f"👥 Usuarios ({len(user_list)})",
                value="\n".join(user_list),
                inline=False
            )

        embed.add_field(
            name="⏰ Hora actual México",
            value=mexico_now.strftime("%H:%M:%S"),
            inline=True
        )

        embed.add_field(
            name="🕐 Próximo inicio",
            value=f"{START_TIME_HOUR}:{START_TIME_MINUTE:02d} México",
            inline=True
        )

        embed.set_footer(text=f"Los tiempos se iniciarán automáticamente a las {START_TIME_HOUR}:{START_TIME_MINUTE:02d} México")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message("❌ Error al obtener usuarios pre-registrados.", ephemeral=True)
        print(f"Error obteniendo pre-registrados: {e}")

@bot.tree.command(name="mi_tiempo", description="Ver tu propio tiempo registrado")
async def mi_tiempo(interaction: discord.Interaction):
    """Comando para que los usuarios vean su propio tiempo"""
    try:
        user_id = interaction.user.id
        user_data = time_tracker.get_user_data(user_id)

        if not user_data:
            await interaction.response.send_message(
                "❌ No tienes tiempo registrado aún. Un administrador debe iniciarte el tiempo primero.",
                ephemeral=True
            )
            return

        total_time = time_tracker.get_total_time(user_id)
        formatted_time = time_tracker.format_time_human(total_time)

        # Obtener tipo de rol del usuario
        member = interaction.guild.get_member(user_id) if interaction.guild else None
        role_type = get_user_role_type(member) if member else "normal"

        # Crear embed con información del usuario
        embed = discord.Embed(
            title=f"⏰ Tu Tiempo - {interaction.user.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        embed.add_field(name="⏱️ Tiempo Total", value=formatted_time, inline=True)

        # Determinar estado
        total_hours = total_time / 3600

        # Verificar si ha completado su tiempo máximo
        is_finished = (user_data.get("milestone_completed", False) or
                      (role_type == "gold" and total_hours >= 2.0) or
                      (role_type == "normal" and total_hours >= 1.0))

        if user_data.get('is_active', False):
            status = "🟢 Activo"
        elif is_finished:
            status = "✅ Terminado"
        elif user_data.get('is_paused', False):
            status = "⏸️ Pausado"
        else:
            status = "🔴 Inactivo"

        embed.add_field(name="📍 Estado", value=status, inline=True)

        # Mostrar tiempo pausado si aplica
        if user_data.get('is_paused', False):
            paused_duration = time_tracker.get_paused_duration(user_id)
            formatted_paused_time = time_tracker.format_time_human(paused_duration) if paused_duration > 0 else "0 Segundos"
            embed.add_field(
                name="⏸️ Tiempo Pausado",
                value=formatted_paused_time,
                inline=False
            )

        # Mostrar contador de pausas si hay
        pause_count = time_tracker.get_pause_count(user_id)
        if pause_count > 0:
            pause_text = "pausa" if pause_count == 1 else "pausas"
            embed.add_field(
                name="📊 Pausas",
                value=f"{pause_count} {pause_text} de 3 máximo",
                inline=True
            )

        # Mostrar créditos ganados
        credits = calculate_credits(total_time, role_type)
        embed.add_field(
            name="💰 Créditos Ganados",
            value=f"{credits} créditos",
            inline=True
        )

        # Mostrar límites según rol
        if role_type == "gold":
            embed.add_field(
                name="🎭 Tu Rol",
                value="🏆 Gold - Límite: 2 horas",
                inline=False
            )
        else:
            embed.add_field(
                name="🎭 Tu Rol",
                value="👤 Recluta - Límite: 1 hora",
                inline=False
            )

        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.set_footer(text="Tu información personal de tiempo")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    except Exception as e:
        await interaction.response.send_message("❌ Error al obtener tu información de tiempo.", ephemeral=True)
        print(f"Error en comando mi_tiempo para {interaction.user.display_name}: {e}")



# =================== COMANDOS DE PAGO SIMPLIFICADOS ===================

class PaymentMainView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=300)
        self.guild = guild

    @discord.ui.select(
        placeholder="Selecciona el tipo de usuarios a ver...",
        options=[
            discord.SelectOption(
                label="Reclutas (Sin Rol)",
                value="reclutas",
                description="Ver usuarios sin rol específico",
                emoji="👤"
            ),
            discord.SelectOption(
                label="Gold",
                value="gold",
                description="Ver usuarios con rol Gold",
                emoji="🏆"
            )
        ]
    )
    async def select_payment_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_type = select.values[0]

        try:
            await interaction.response.defer()

            if selected_type == "reclutas":
                # Lógica de reclutas
                def filter_normal_users(member, data):
                    if not member:
                        return True
                    role_type = get_user_role_type(member)
                    return role_type == "normal"

                filtered_users = get_users_by_role_filter(filter_normal_users, "Reclutas (Sin Rol)", interaction)
                role_name = "Reclutas (Sin Rol)"

            else:  # reclutas
                # Lógica de Gold
                def filter_gold_users(member, data):
                    if not member:
                        return False
                    if GOLD_ROLE_ID:
                        for role in member.roles:
                            if role.id == GOLD_ROLE_ID:
                                return True
                    role_type = get_user_role_type(member)
                    return role_type == "gold"

                filtered_users = get_users_by_role_filter(filter_gold_users, "Gold", interaction)
                role_name = "Gold"

            if not filtered_users:
                error_embed = discord.Embed(
                    title="❌ Sin Resultados",
                    description=f"No se encontraron usuarios para {role_name} con tiempo registrado",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=error_embed, view=self)
                return

            # Crear vista con resultados y actualizar mensaje existente
            view = PaymentView(filtered_users, role_name, self.guild)
            embed = view.get_embed()
            await interaction.edit_original_response(embed=embed, view=view)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Error cargando datos: {e}",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=error_embed, view=self)

    @discord.ui.button(label='🔄 Actualizar', style=discord.ButtonStyle.success)
    async def refresh_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo actualizar la vista principal, no recargar datos hasta que seleccionen una opción
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class PaymentView(discord.ui.View):
    def __init__(self, filtered_users, role_name, guild, search_term=None):
        super().__init__(timeout=300)
        self.filtered_users = filtered_users
        self.role_name = role_name
        self.guild = guild
        self.search_term = search_term
        self.current_page = 0
        self.max_per_page = 15
        self.total_pages = (len(filtered_users) + self.max_per_page - 1) // self.max_per_page if filtered_users else 1

        if self.total_pages <= 1:
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.label in ['◀️ Anterior', '▶️ Siguiente']:
                    item.disabled = True

    def get_embed(self):
        """Crear embed para la página actual"""
        start_idx = self.current_page * self.max_per_page
        end_idx = min(start_idx + self.max_per_page, len(self.filtered_users))
        current_users = self.filtered_users[start_idx:end_idx]

        role_emoji = "👤"
        if "Gold" in self.role_name:
            role_emoji = "🏆"

        title = f"{role_emoji} Pago - {self.role_name}"
        if self.search_term:
            title += f" (Búsqueda: '{self.search_term}')"

        embed = discord.Embed(
            title=title,
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )

        if not current_users:
            embed.description = f"No se encontraron usuarios para {self.role_name}"
            if self.search_term:
                embed.description += f" con el término '{self.search_term}'"
            embed.set_footer(text="No hay datos para mostrar")
            return embed

        user_list = []
        total_credits = 0

        for user_data in current_users:
            try:
                user_id = user_data['user_id']
                member = self.guild.get_member(user_id) if self.guild else None

                if member:
                    user_mention = member.mention
                else:
                    user_name = user_data.get('name', f'Usuario {user_id}')
                    user_mention = f"**{user_name}** `(ID: {user_id})`"

                total_time = user_data['total_time']
                formatted_time = time_tracker.format_time_human(total_time)
                credits = user_data['credits']
                total_credits += credits

                data = user_data.get('data', {})
                status = "🔴 Inactivo"
                if data.get('is_active', False):
                    status = "🟢 Activo"
                elif data.get('is_paused', False):
                    total_hours = total_time / 3600
                    role_type = get_user_role_type(member) if member else "normal"

                    if (data.get("milestone_completed", False) or
                        (role_type == "gold" and total_hours >= 2.0) or
                        (role_type == "normal" and total_hours >= 1.0)):
                        status = "✅ Terminado"
                    else:
                        status = "⏸️ Pausado"
                else:
                    # Verificar si está terminado aunque no esté pausado
                    total_hours = total_time / 3600
                    role_type = get_user_role_type(member) if member else "normal"

                    if (data.get("milestone_completed", False) or
                        (role_type == "gold" and total_hours >= 2.0) or
                        (role_type == "normal" and total_hours >= 1.0)):
                        status = "✅ Terminado"


                user_list.append(f"📌 {user_mention} - ⏱️ {formatted_time} - 💰 {credits} Créditos {status}")

            except Exception as e:
                print(f"Error procesando usuario en pago: {e}")
                continue

        embed.description = "\n".join(user_list)

        embed.add_field(
            name="📊 Resumen de Página",
            value=f"Usuarios: {len(current_users)}\nCréditos en página: {total_credits}",
            inline=True
        )

        total_users = len(self.filtered_users)
        total_all_credits = sum(user['credits'] for user in self.filtered_users)

        embed.add_field(
            name="🎯 Total General",
            value=f"Usuarios: {total_users}\nCréditos totales: {total_all_credits}",
            inline=True
        )

        embed.set_footer(text=f"Página {self.current_page + 1}/{self.total_pages} • {total_users} usuarios en total")
        return embed

    @discord.ui.button(label='◀️ Anterior', style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='▶️ Siguiente', style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='🔍 Buscar Usuario', style=discord.ButtonStyle.primary)
    async def search_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SearchUserModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🔄 Actualizar', style=discord.ButtonStyle.success)
    async def refresh_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()

            # Determinar el tipo de filtro basado en el nombre del rol
            if "Gold" in self.role_name:
                def filter_func(member, data):
                    if not member:
                        return False
                    if GOLD_ROLE_ID:
                        for role in member.roles:
                            if role.id == GOLD_ROLE_ID:
                                return True
                    role_type = get_user_role_type(member)
                    return role_type == "gold"
            else:  # Reclutas
                def filter_func(member, data):
                    if not member:
                        return True
                    role_type = get_user_role_type(member)
                    return role_type == "normal"

            # Recargar datos
            refreshed_users = get_users_by_role_filter(filter_func, self.role_name, interaction)

            # Aplicar filtro de búsqueda si existe
            if self.search_term and refreshed_users:
                search_filtered = []
                for user_data in refreshed_users:
                    user_name = user_data.get('name', '').lower()
                    if self.search_term.lower() in user_name:
                        search_filtered.append(user_data)
                refreshed_users = search_filtered

            # Actualizar datos internos
            self.filtered_users = refreshed_users
            self.total_pages = (len(refreshed_users) + self.max_per_page - 1) // self.max_per_page if refreshed_users else 1

            # Asegurar que la página actual sea válida
            if self.current_page >= self.total_pages:
                self.current_page = max(0, self.total_pages - 1)

            # Actualizar botones
            self.update_buttons()

            # Obtener embed actualizado
            embed = self.get_embed()

            # Actualizar mensaje existente sin reenviar
            await interaction.edit_original_response(embed=embed, view=self)

        except Exception as e:
            await interaction.followup.send(f"❌ Error al actualizar: {e}", ephemeral=True)

    @discord.ui.button(label='🔄 Limpiar búsqueda', style=discord.ButtonStyle.secondary)
    async def clear_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.search_term:
            await interaction.response.send_message("❌ No hay búsqueda activa para limpiar", ephemeral=True)
            return

        try:
            await interaction.response.defer()

            # Determinar el tipo de filtro basado en el nombre del rol
            if "Gold" in self.role_name:
                def filter_func(member, data):
                    if not member:
                        return False
                    if GOLD_ROLE_ID:
                        for role in member.roles:
                            if role.id == GOLD_ROLE_ID:
                                return True
                    role_type = get_user_role_type(member)
                    return role_type == "gold"
            else:  # Reclutas
                def filter_func(member, data):
                    if not member:
                        return True
                    role_type = get_user_role_type(member)
                    return role_type == "normal"

            # Recargar datos sin filtro de búsqueda
            all_users = get_users_by_role_filter(filter_func, self.role_name, interaction)

            if not all_users:
                await interaction.edit_original_response(content="❌ No se encontraron usuarios para mostrar")
                return

            # Crear nueva vista sin filtro de búsqueda
            new_view = PaymentView(all_users, self.role_name, self.guild)
            embed = new_view.get_embed()

            await interaction.edit_original_response(embed=embed, view=new_view)

        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error al recargar: {e}")

    @discord.ui.select(
        placeholder="Cambiar tipo de usuarios...",
        options=[
            discord.SelectOption(
                label="Reclutas (Sin Rol)",
                value="reclutas",
                description="Ver usuarios sin rol específico",
                emoji="👤"
            ),
            discord.SelectOption(
                label="Gold",
                value="gold",
                description="Ver usuarios con rol Gold",
                emoji="🏆"
            )
        ]
    )
    async def select_payment_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_type = select.values[0]

        try:
            await interaction.response.defer()

            if selected_type == "reclutas":
                # Lógica de reclutas
                def filter_normal_users(member, data):
                    if not member:
                        return True
                    role_type = get_user_role_type(member)
                    return role_type == "normal"

                filtered_users = get_users_by_role_filter(filter_normal_users, "Reclutas (Sin Rol)", interaction)
                role_name = "Reclutas (Sin Rol)"

            else:  # reclutas
                # Lógica de Gold
                def filter_gold_users(member, data):
                    if not member:
                        return False
                    if GOLD_ROLE_ID:
                        for role in member.roles:
                            if role.id == GOLD_ROLE_ID:
                                return True
                    role_type = get_user_role_type(member)
                    return role_type == "gold"

                filtered_users = get_users_by_role_filter(filter_gold_users, "Gold", interaction)
                role_name = "Gold"

            if not filtered_users:
                error_embed = discord.Embed(
                    title="❌ Sin Resultados",
                    description=f"No se encontraron usuarios para {role_name} con tiempo registrado",
                    color=discord.Color.red()
                )
                # Mantener la vista actual pero con mensaje de error
                await interaction.edit_original_response(embed=error_embed, view=self)
                return

            # Actualizar datos internos y crear nueva vista
            new_view = PaymentView(filtered_users, role_name, self.guild)
            embed = new_view.get_embed()
            await interaction.edit_original_response(embed=embed, view=new_view)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Error cargando datos: {e}",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=error_embed, view=self)

    @discord.ui.button(label='🔙 Volver al Menú', style=discord.ButtonStyle.secondary)
    async def back_to_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()

            # Crear embed del menú principal
            embed = discord.Embed(
                title="💰 Sistema de Pagos",
                description="Selecciona el tipo de usuarios que deseas ver:",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            embed.add_field(
                name="👤 Reclutas (Sin Rol)",
                value="• Límite: 1 hora\n• Créditos: 3 por hora completada",
                inline=True
            )

            embed.add_field(
                name="🏆 Gold",
                value="• Límite: 2 horas\n• 1 hora: 5 créditos\n• 2 horas: 10 créditos",
                inline=True
            )

            embed.add_field(
                name="ℹ️ Instrucciones",
                value="Usa el menú desplegable para seleccionar qué usuarios ver",
                inline=False
            )

            embed.set_footer(text="Sistema de créditos simplificado")

            # Volver a la vista del menú principal
            main_view = PaymentMainView(self.guild)
            await interaction.edit_original_response(embed=embed, view=main_view)

        except Exception as e:
            await interaction.followup.send(f"❌ Error al volver al menú: {e}", ephemeral=True)

    def update_buttons(self):
        """Actualizar estado de los botones"""
        self.children[0].disabled = (self.current_page == 0)
        self.children[1].disabled = (self.current_page >= self.total_pages - 1)

    async def on_timeout(self):
        """Deshabilitar botones cuando expire"""
        for item in self.children:
            item.disabled = True

class SearchUserModal(discord.ui.Modal):
    def __init__(self, payment_view):
        super().__init__(title='Buscar Usuario')
        self.payment_view = payment_view

    search_term = discord.ui.TextInput(
        label='Nombre del usuario',
        placeholder='Escribe parte del nombre del usuario...',
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        search_term = self.search_term.value.lower().strip()

        matching_users = []
        for user_data in self.payment_view.filtered_users:
            user_name = user_data.get('name', '').lower()
            if search_term in user_name:
                matching_users.append(user_data)

        if not matching_users:
            await interaction.response.send_message(
                f"❌ No se encontraron usuarios con '{self.search_term.value}' en {self.payment_view.role_name}",
                ephemeral=True
            )
            return

        new_view = PaymentView(matching_users, self.payment_view.role_name, self.payment_view.guild, search_term)
        embed = new_view.get_embed()

        await interaction.response.edit_message(embed=embed, view=new_view)

def get_users_by_role_filter(role_filter_func, role_name: str, interaction: discord.Interaction):
    """Función auxiliar para obtener usuarios filtrados por rol"""
    try:
        tracked_users = time_tracker.get_all_tracked_users()
        filtered_users = []

        for user_id_str, data in tracked_users.items():
            try:
                user_id = int(user_id_str)
                member = interaction.guild.get_member(user_id) if interaction.guild else None

                if not role_filter_func(member, data):
                    continue

                total_time = time_tracker.get_total_time(user_id)

                if total_time <= 0:
                    continue

                if member:
                    role_type = get_user_role_type(member)
                else:
                    role_type = "normal"

                credits = calculate_credits(total_time, role_type)

                user_info = {
                    'user_id': user_id,
                    'name': data.get('name', f'Usuario {user_id}'),
                    'total_time': total_time,
                    'credits': credits,
                    'role_type': role_type,
                    'data': data
                }

                filtered_users.append(user_info)

            except Exception as e:
                print(f"Error procesando usuario {user_id_str}: {e}")
                continue

        filtered_users.sort(key=lambda x: x['name'].lower())
        return filtered_users

    except Exception as e:
        print(f"Error en get_users_by_role_filter: {e}")
        return []



@bot.tree.command(name="pagas", description="Ver sistema de pagos con dropdown de opciones")
@is_admin()
async def pagas(interaction: discord.Interaction):
    """Comando principal de pagos con dropdown para seleccionar tipo de usuario"""
    try:
        embed = discord.Embed(
            title="💰 Sistema de Pagos",
            description="Selecciona el tipo de usuarios que deseas ver:",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="👤 Reclutas (Sin Rol)",
            value="• Límite: 1 hora\n• Créditos: 3 por hora completada",
            inline=True
        )

        embed.add_field(
            name="🏆 Gold",
            value="• Límite: 2 horas\n• 1 hora: 5 créditos\n• 2 horas: 10 créditos",
            inline=True
        )

        embed.add_field(
            name="ℹ️ Instrucciones",
            value="Usa el menú desplegable para seleccionar qué usuarios ver",
            inline=False
        )

        embed.set_footer(text="Sistema de créditos simplificado")

        view = PaymentMainView(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al mostrar sistema de pagos: {e}", ephemeral=True)

# =================== NOTIFICACIONES ===================

async def send_milestone_notification(user_name: str, member, is_external_user: bool, hours: int, total_time: float):
    """Enviar notificación cuando un usuario completa un milestone de hora"""
    try:
        channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
        if not channel:
            print(f"❌ Canal de notificaciones no encontrado: {NOTIFICATION_CHANNEL_ID}")
            return

        # Determinar tipo de rol y calcular créditos
        role_type = "normal"
        if member:
            role_type = get_user_role_type(member)

        # Calcular créditos basado en las horas y tipo de rol
        credits = calculate_credits(total_time, role_type)

        # Crear mención del usuario si es posible
        user_mention = member.mention if member else f"**{user_name}**"

        # Crear mensaje según el tipo de usuario SIN mostrar tiempo total detallado
        if role_type == "gold":
            if hours == 1:
                message = f"{user_mention} ha completado **1 hora** ( {credits} Créditos / Gold )\n🔄 **¡Puede continuar 1 hora más!**"
            elif hours == 2:
                message = f"{user_mention} ha completado **2 horas** ( {credits} Créditos / Gold )\n✅ **¡Máximo alcanzado!**"
            else:
                message = f"{user_mention} ha completado **{hours} hora{'s' if hours != 1 else ''}** ( {credits} Créditos / Gold )\n🔄 **Puede continuar hasta 2 horas**"
        else:
            if hours == 1:
                message = f"{user_mention} ha completado **1 hora** ( {credits} Créditos / Recluta )\n✅ **¡Máximo alcanzado!**"
            else:
                message = f"{user_mention} ha completado **{hours} hora{'s' if hours != 1 else ''}** ( {credits} Créditos / Recluta )"

        await channel.send(message)

    except Exception as e:
        print(f"❌ Error enviando notificación de milestone para {user_name}: {e}")

async def send_auto_cancellation_notification(user_name: str, total_time: str, cancelled_by: str, pause_count: int, time_lost: float = 0):
    """Enviar notificación cuando un usuario es cancelado automáticamente por 3 pausas"""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            channel = bot.get_channel(CANCELLATION_NOTIFICATION_CHANNEL_ID)
            if not channel:
                print(f"❌ Canal de cancelaciones no encontrado: {CANCELLATION_NOTIFICATION_CHANNEL_ID}")
                return

            formatted_time_lost = time_tracker.format_time_human(time_lost) if time_lost > 0 else "0 Segundos"
            message = f"🚫 **Tiempo Cancelado Automáticamente**\n**{user_name}** ha sido cancelado automáticamente por exceder el límite de pausas\n**Tiempo conservado:** {total_time} (solo horas completas)\n**Tiempo perdido:** {formatted_time_lost}\n**Pausas alcanzadas:** {pause_count}/3\n**Última pausa ejecutada por:** {cancelled_by}"

            await asyncio.wait_for(channel.send(message), timeout=10.0)
            print(f"✅ Notificación de cancelación automática enviada para {user_name} al canal {CANCELLATION_NOTIFICATION_CHANNEL_ID}")
            return

        except asyncio.TimeoutError:
            print(f"⚠️ Timeout enviando notificación de cancelación automática para {user_name} (intento {attempt + 1}/{max_retries})")
        except Exception as e:
            print(f"⚠️ Error enviando notificación de cancelación automática para {user_name} (intento {attempt + 1}): {e}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)

    print(f"❌ CRÍTICO: No se pudo enviar notificación de cancelación automática para {user_name} después de {max_retries} intentos")

async def send_cancellation_notification(user_name: str, cancelled_by: str, total_time: str = "", conserved_time: str = "", lost_time: str = ""):
    """Enviar notificación cuando un usuario es cancelado"""
    channel = bot.get_channel(CANCELLATION_NOTIFICATION_CHANNEL_ID)
    if channel:
        try:
            if conserved_time and lost_time:
                message = f"🗑️ El seguimiento de tiempo de **{user_name}** ha sido cancelado\n**Tiempo total:** {total_time}\n**Tiempo conservado:** {conserved_time} (horas completas)\n**Tiempo perdido:** {lost_time}\n**Cancelado por:** {cancelled_by}"
            elif conserved_time:
                message = f"🗑️ El seguimiento de tiempo de **{user_name}** ha sido cancelado\n**Tiempo conservado:** {conserved_time}\n**Cancelado por:** {cancelled_by}"
            elif total_time:
                message = f"🗑️ El seguimiento de tiempo de **{user_name}** ha sido cancelado\n**Tiempo cancelado:** {total_time}\n**Cancelado por:** {cancelled_by}"
            else:
                message = f"🗑️ El seguimiento de tiempo de **{user_name}** ha sido cancelado por {cancelled_by}"
            await channel.send(message)
            print(f"✅ Notificación de cancelación enviada para {user_name}")
        except Exception as e:
            print(f"❌ Error enviando notificación de cancelación: {e}")

async def send_pause_notification(user_name: str, total_time: float, paused_by: str, session_time: str = "", pause_count: int = 0, role_type: str = "normal"):
    """Enviar notificación cuando un usuario es pausado"""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            channel = bot.get_channel(PAUSE_NOTIFICATION_CHANNEL_ID)
            if not channel:
                print(f"❌ Canal de pausas no encontrado: {PAUSE_NOTIFICATION_CHANNEL_ID}")
                return

            formatted_total_time = time_tracker.format_time_human(total_time)

            # Mensaje específico para usuarios Gold
            if role_type == "gold":
                message = f"⏸️ El tiempo de **{user_name}** ha sido pausado por {paused_by}\n**Tiempo total acumulado:** {formatted_total_time}\n📊 **{user_name}** Pausas Ilimitadas sin penalización (Gold)"
            else:
                # Mensaje para usuarios normales/reclutas con formato X/3
                if session_time and session_time != "0 Segundos":
                    message = f"⏸️ El tiempo de **{user_name}** ha sido pausado\n**Tiempo de sesión pausado:** {session_time}\n**Tiempo total acumulado:** {formatted_total_time}\n**Pausado por:** {paused_by}\n📊 **{user_name}** lleva {pause_count}/3 pausas"
                else:
                    message = f"⏸️ El tiempo de **{user_name}** ha sido pausado por {paused_by}\n**Tiempo total acumulado:** {formatted_total_time}\n📊 **{user_name}** lleva {pause_count}/3 pausas"

                # Agregar advertencia cuando llegue a 2/3 pausas
                if pause_count == 2:
                    message += f"\n⚠️ **ADVERTENCIA:** Si se pausa **{user_name}** una vez más, se eliminarán los minutos acumulados y solo se conservarán las horas completas."

            await channel.send(message)
            return

        except asyncio.TimeoutError:
            print(f"⚠️ Timeout enviando notificación de pausa para {user_name} (intento {attempt + 1}/{max_retries})")
        except Exception as e:
            print(f"⚠️ Error enviando notificación de pausa para {user_name} (intento {attempt + 1}): {e}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)

async def send_unpause_notification(user_name: str, total_time: float, unpaused_by: str, paused_duration: str = ""):
    """Enviar notificación cuando un usuario es despausado"""
    try:
        channel = bot.get_channel(PAUSE_NOTIFICATION_CHANNEL_ID)
        if not channel:
            return

        formatted_total_time = time_tracker.format_time_human(total_time)

        if paused_duration:
            message = f"⏸️ El tiempo de **{user_name}** ha sido despausado\n**Tiempo total acumulado:** {formatted_total_time}\n**Tiempo pausado:** {paused_duration}\n**Despausado por:** {unpaused_by}"
        else:
            message = f"⏸️ El tiempo de **{user_name}** ha sido despausado por {unpaused_by}"

        await asyncio.wait_for(channel.send(message), timeout=15.0)

    except asyncio.TimeoutError:
        print(f"⚠️ Timeout enviando notificación de despausa para {user_name}")
    except Exception as e:
        print(f"⚠️ Error enviando notificación de despausa para {user_name}: {e}")

async def check_time_milestone_for_gold_users(user_id: int, user_name: str, member, user_data: dict):
    """Lógica específica para usuarios Gold - Detener automáticamente a las 2 horas"""
    try:
        if not user_data.get('is_active', False) or not user_data.get('last_start'):
            return

        total_time = time_tracker.get_total_time(user_id)
        total_hours = total_time / 3600

        if 'notified_milestones' not in user_data:
            user_data['notified_milestones'] = []
            time_tracker.save_data()

        notified_milestones = user_data.get('notified_milestones', [])

        # Verificar si completó 2 horas EXACTAS y detener automáticamente
        if total_hours >= 2.0 and 7200 not in notified_milestones:
            # Detener el seguimiento
            time_tracker.stop_tracking(user_id)

            # Marcar como completado
            user_data_refresh = time_tracker.get_user_data(user_id)
            if user_data_refresh:
                user_data_refresh['milestone_completed'] = True
                user_data_refresh['notified_milestones'].append(7200)
                time_tracker.save_data()

            # Enviar notificación de completado
            await send_milestone_notification(user_name, member, False, 2, total_time)
            return

        # Notificar milestone de 1 hora si no se ha notificado
        if total_hours >= 1.0 and 3600 not in notified_milestones:
            notified_milestones.append(3600)
            user_data['notified_milestones'] = notified_milestones
            time_tracker.save_data()
            await send_milestone_notification(user_name, member, False, 1, total_time)

    except Exception as e:
        print(f"❌ Error en check_time_milestone_for_gold_users para {user_name}: {e}")
        import traceback
        traceback.print_exc()

async def check_time_milestone_for_normal_users(user_id: int, user_name: str, member, user_data: dict):
    """Lógica específica para usuarios normales/reclutas - Detener automáticamente a 1 hora"""
    try:
        if not user_data.get('is_active', False) or not user_data.get('last_start'):
            return

        total_time = time_tracker.get_total_time(user_id)
        total_hours = total_time / 3600

        if 'notified_milestones' not in user_data:
            user_data['notified_milestones'] = []
            time_tracker.save_data()

        notified_milestones = user_data.get('notified_milestones', [])

        # Verificar si completó 1 hora EXACTA y detener automáticamente
        if total_hours >= 1.0 and 3600 not in notified_milestones:
            # Detener el seguimiento
            time_tracker.stop_tracking(user_id)

            # Marcar como completado
            user_data_refresh = time_tracker.get_user_data(user_id)
            if user_data_refresh:
                user_data_refresh['milestone_completed'] = True
                user_data_refresh['notified_milestones'].append(3600)
                time_tracker.save_data()

            # Enviar notificación de completado
            await send_milestone_notification(user_name, member, False, 1, total_time)

    except Exception as e:
        print(f"❌ Error en check_time_milestone_for_normal_users para {user_name}: {e}")
        import traceback
        traceback.print_exc()



async def check_time_milestone(user_id: int, user_name: str):
    """Verificar milestones y dirigir a la función específica según el tipo de usuario"""
    try:
        user_data = time_tracker.get_user_data(user_id)
        if not user_data:
            return

        guild = None
        member = None
        try:
            guild = bot.guilds[0] if bot.guilds else None
            if guild:
                member = guild.get_member(user_id)
        except Exception as e:
            print(f"⚠️ Error obteniendo miembro del servidor para {user_name}: {e}")

        # Determinar tipo de usuario y dirigir a función específica
        if member:
            role_type = get_user_role_type(member)

            if role_type == "gold":
                # Usuario Gold - hasta 2 horas
                await check_time_milestone_for_gold_users(user_id, user_name, member, user_data)
            else:
                # Usuario normal/recluta - hasta 1 hora
                await check_time_milestone_for_normal_users(user_id, user_name, member, user_data)
        else:
            # Si no se puede obtener el miembro, asumir usuario normal
            await check_time_milestone_for_normal_users(user_id, user_name, None, user_data)

    except Exception as e:
        print(f"❌ Error crítico en check_time_milestone para {user_name}: {e}")
        import traceback
        traceback.print_exc()

async def periodic_milestone_check():
    """Verificar milestones periódicamente para usuarios activos con optimización de recursos"""
    milestone_check_count = 0
    error_count = 0
    max_errors = 3
    last_check_time = 0

    while True:
        try:
            # Intervalo adaptativo basado en carga
            sleep_interval = 15 if error_count == 0 else min(30 + (error_count * 10), 60)
            await asyncio.sleep(sleep_interval)

            current_time = asyncio.get_event_loop().time()
            milestone_check_count += 1

            # Verificación de milestones perdidos cada 2 minutos - función removida por simplicidad
            # if milestone_check_count % 8 == 1:
            #     print("⚠️ Verificación de milestones perdidos deshabilitada")

            # Optimización: solo verificar usuarios activos si ha pasado suficiente tiempo
            if current_time - last_check_time < 10:
                continue

            try:
                tracked_users = await asyncio.wait_for(
                    asyncio.to_thread(time_tracker.get_all_tracked_users),
                    timeout=30.0
                )

                # Filtrar solo usuarios realmente activos
                active_users = [
                    (user_id_str, data) for user_id_str, data in tracked_users.items()
                    if data.get('is_active', False) and not data.get('is_paused', False)
                ]

                # Límite aumentado pero con mejor control
                max_active_users = 120
                active_users = active_users[:max_active_users]

                if not active_users:
                    last_check_time = current_time
                    continue

                # Usar semáforo para controlar concurrencia
                semaphore = asyncio.Semaphore(6)  # Máximo 6 operaciones concurrentes

                async def process_user_milestone(user_id_str, data):
                    async with semaphore:
                        try:
                            user_id = int(user_id_str)
                            user_name = data.get('name', f'Usuario {user_id}')

                            await asyncio.wait_for(
                                check_time_milestone(user_id, user_name),
                                timeout=20.0
                            )
                        except asyncio.TimeoutError:
                            print(f"⚠️ Timeout verificando milestone para {user_id_str}")
                        except Exception as e:
                            print(f"⚠️ Error verificando milestone para {user_id_str}: {e}")

                # Procesar en lotes controlados
                batch_size = 15
                for i in range(0, len(active_users), batch_size):
                    batch = active_users[i:i + batch_size]

                    tasks = [
                        process_user_milestone(user_id_str, data)
                        for user_id_str, data in batch
                    ]

                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*tasks, return_exceptions=True),
                            timeout=45.0
                        )
                    except asyncio.TimeoutError:
                        print(f"⚠️ Timeout en lote {i//batch_size + 1} de milestones")

                    # Pausa entre lotes para no sobrecargar
                    if i + batch_size < len(active_users):
                        await asyncio.sleep(0.3)

                last_check_time = current_time

            except asyncio.TimeoutError:
                print("⚠️ Timeout obteniendo usuarios activos")
            except Exception as e:
                print(f"⚠️ Error obteniendo usuarios activos: {e}")

            error_count = 0

        except Exception as e:
            error_count += 1
            print(f"❌ Error en verificación periódica de milestones (#{error_count}): {e}")

            if error_count >= max_errors:
                print(f"🚨 Demasiados errores consecutivos ({error_count}). Pausando verificaciones por 90 segundos...")
                await asyncio.sleep(90)
                error_count = 0
            else:
                sleep_time = min(20 * (2 ** error_count), 120)
                await asyncio.sleep(sleep_time)

async def auto_start_at_1pm():
    """Verificar y iniciar automáticamente tiempos a las 19:00 México"""
    while True:
        try:
            await asyncio.sleep(30)  # Verificar cada 30 segundos

            mexico_now = datetime.now(MEXICO_TZ)
            current_hour = mexico_now.hour
            current_minute = mexico_now.minute

            # Verificar si son exactamente las 19:00 (solo en el minuto exacto)
            if current_hour == START_TIME_HOUR and current_minute == START_TIME_MINUTE:
                print(f"🕐 Son las {START_TIME_HOUR}:{START_TIME_MINUTE:02d} México - Iniciando tiempos automáticamente...")

                # Obtener usuarios pre-registrados
                pre_registered_users = time_tracker.get_pre_registered_users()

                if pre_registered_users:
                    started_users = []

                    for user_id_str, data in pre_registered_users.items():
                        user_id = int(user_id_str)
                        user_name = data.get('name', f'Usuario {user_id}')

                        # Obtener información del admin que hizo el pre-registro
                        initiator_info = time_tracker.get_pre_register_initiator(user_id)

                        # Iniciar tiempo automáticamente
                        success = time_tracker.start_tracking_from_pre_register(user_id)
                        if success:
                            # Intentar obtener el objeto del miembro para la mención
                            member = None
                            try:
                                if bot.guilds:
                                    guild = bot.guilds[0]
                                    member = guild.get_member(user_id)
                            except Exception as e:
                                print(f"⚠️ Error obteniendo miembro para notificación: {e}")

                            # Usar mención si es posible, sino usar nombre
                            if member:
                                user_reference = member.mention
                            else:
                                user_reference = f"**{user_name}**"

                            if initiator_info:
                                admin_name = initiator_info.get('admin_name', 'Admin desconocido')
                                started_users.append(f"• {user_reference} - Pre-registrado por: {admin_name}")
                            else:
                                started_users.append(f"• {user_reference} - Pre-registrado por: Admin desconocido")

                    if started_users:
                        # Notificación automática deshabilitada
                        # await send_auto_start_notification(started_users, mexico_now)
                        print(f"✅ Iniciados automáticamente {len(started_users)} usuarios a las 19:00 México (sin notificación)")

                # Esperar 70 segundos para evitar múltiples ejecuciones
                await asyncio.sleep(70)

        except Exception as e:
            print(f"❌ Error en auto-inicio a las 19:00 México: {e}")
            await asyncio.sleep(30)

async def auto_stop_at_2225():
    """Detener automáticamente todos los tiempos a las 21:21 (21:20 PM) hora México"""
    while True:
        try:
            await asyncio.sleep(30)  # Verificar cada 30 segundos

            mexico_now = datetime.now(MEXICO_TZ)
            current_hour = mexico_now.hour
            current_minute = mexico_now.minute

            # Verificar si son exactamente las 22:25 (10:25 PM)
            if current_hour == 21 and current_minute == 21:
                print(f"🛑 Son las 22:25 México - Deteniendo todos los tiempos automáticamente...")

                # Obtener todos los usuarios con tiempo activo
                tracked_users = time_tracker.get_all_tracked_users()
                stopped_count = 0

                for user_id_str, data in tracked_users.items():
                    if data.get('is_active', False) or data.get('is_paused', False):
                        user_id = int(user_id_str)
                        
                        # Detener el tiempo
                        success = time_tracker.stop_tracking(user_id)
                        if success:
                            stopped_count += 1
                            user_name = data.get('name', f'Usuario {user_id}')
                            print(f"  ✅ Detenido tiempo de {user_name}")

                if stopped_count > 0:
                    print(f"✅ Detenidos automáticamente {stopped_count} usuarios a las 22:25 México")

                # Esperar 70 segundos para evitar múltiples ejecuciones
                await asyncio.sleep(70)

        except Exception as e:
            print(f"❌ Error en detención automática a las 22:25 México: {e}")
            await asyncio.sleep(30)

async def start_periodic_checks():
    """Iniciar las verificaciones periódicas"""
    global milestone_check_task, auto_start_task, auto_stop_task

    if milestone_check_task is None:
        milestone_check_task = bot.loop.create_task(periodic_milestone_check())
        print('✅ Task de verificación de milestones iniciado')

    if auto_start_task is None:
        auto_start_task = bot.loop.create_task(auto_start_at_1pm())
        print('✅ Task de inicio automático a las 19:00 México iniciado')
    
    if 'auto_stop_task' not in globals() or auto_stop_task is None:
        auto_stop_task = bot.loop.create_task(auto_stop_at_2225())
        print('✅ Task de detención automática a las 21:21 México iniciado')

@bot.event
async def on_connect():
    """Evento que se ejecuta cuando el bot se conecta"""
    await start_periodic_checks()

# =================== MANEJO DE ERRORES ===================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    try:
        command_name = interaction.command.name if interaction.command else 'desconocido'
        print(f"Error en comando /{command_name}: {type(error).__name__}")

        if isinstance(error, discord.app_commands.CommandInvokeError):
            original_error = error.original if hasattr(error, 'original') else error

            if isinstance(original_error, discord.NotFound) and "10062" in str(original_error):
                print(f"⚠️ Interacción /{command_name} expirada (10062) - no respondiendo")
                return
            elif "Unknown interaction" in str(original_error):
                print(f"⚠️ Interacción /{command_name} desconocida - no respondiendo")
                return

        if isinstance(error, discord.app_commands.CheckFailure):
            error_msg = "❌ No tienes permisos para usar este comando."
        elif isinstance(error, discord.app_commands.CommandInvokeError):
            error_msg = "❌ Error interno del comando. El administrador ha sido notificado."
        elif isinstance(error, discord.app_commands.TransformerError):
            error_msg = "❌ Error en los parámetros. Verifica los valores ingresados."
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            error_msg = f"⏰ Comando en cooldown. Intenta de nuevo en {error.retry_after:.1f}s"
        else:
            error_msg = "❌ Error inesperado. Intenta de nuevo."

        try:
            if not interaction.response.is_done():
                await asyncio.wait_for(
                    interaction.response.send_message(error_msg, ephemeral=True),
                    timeout=2.0
                )
            else:
                await asyncio.wait_for(
                    interaction.followup.send(error_msg, ephemeral=True),
                    timeout=2.0
                )
        except asyncio.TimeoutError:
            print(f"⚠️ Timeout respondiendo a error en /{command_name}")
        except discord.NotFound:
            print(f"⚠️ Interacción /{command_name} no encontrada al responder error")
        except discord.HTTPException as e:
            if "10062" not in str(e):
                print(f"⚠️ Error HTTP respondiendo a /{command_name}: {e}")
        except Exception as e:
            print(f"⚠️ Error inesperado respondiendo a /{command_name}: {e}")

    except Exception as e:
        print(f"❌ Error crítico en manejo global de errores: {e}")

def get_discord_token():
    """Obtener token de Discord de forma segura desde config.json o variables de entorno"""
    if config and config.get('discord_bot_token'):
        token = config.get('discord_bot_token')
        if token and isinstance(token, str) and token.strip():
            print("✅ Token cargado desde config.json")
            return token.strip()

    env_token = os.getenv('DISCORD_BOT_TOKEN')
    if env_token and isinstance(env_token, str) and env_token.strip():
        print("✅ Token cargado desde variables de entorno")
        return env_token.strip()

    print("❌ Error: No se encontró el token de Discord")
    print("┌─ Configura tu token de Discord de una de estas formas:")
    print("│")
    print("│ OPCIÓN 1 (Recomendado): En config.json")
    print("│ Edita config.json y cambia:")
    print('│ "discord_bot_token": "tu_token_aqui"')
    print("│")
    print("│ OPCIÓN 2: Variable de entorno")
    print("│ export DISCORD_BOT_TOKEN='tu_token_aqui'")
    print("└─")
    return None

if __name__ == "__main__":
    print("🤖 Iniciando Discord Time Tracker Bot SIMPLIFICADO...")
    print("📋 Cargando configuración...")

    token = get_discord_token()
    if not token:
        exit(1)

    print("🔗 Conectando a Discord...")
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Error: Token de Discord inválido")
        print("   Verifica que el token sea correcto en config.json")
        print("   O en las variables de entorno si usas esa opción")
    except KeyboardInterrupt:
        print("🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error al iniciar el bot: {e}")
        print("   Revisa la configuración y vuelve a intentar")