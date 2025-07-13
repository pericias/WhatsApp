import streamlit as st
import re
import hashlib # Importamos la librería hashlib para calcular los hashes
import json # Necesario para parsear la configuración de Firebase
import streamlit.components.v1 as components # Para incrustar el componente HTML/JS

def parse_chat_content(chat_content):
    """
    Parses the chat content and returns a list of message dictionaries.
    It also tries to identify all unique participants.
    """
    lines = chat_content.split('\n')
    messages = []
    
    # Use a set to store unique participant names (excluding "Sistema")
    detected_participants = set()

    # Regex to identify the start of a WhatsApp message
    # It handles two main patterns based on the common WhatsApp export format:
    # 1. DATE, TIME - SENDER: MESSAGE (e.g., "2/7/2025, 20:13 - Marcelo G. Montiel: Hola flor")
    # 2. DATE, TIME - MESSAGE (for system messages, e.g., "2/7/2025, 20:13 - Los mensajes...")
    message_regex = re.compile(r"^(\d{1,2}\/\d{1,2}\/\d{4}), (\d{2}:\d{2}) - (?:([^:]+): )?(.*)")

    current_message = None
    for line in lines:
        match = message_regex.match(line)
        if match:
            # If it's the start of a new message
            if current_message:
                messages.append(current_message)

            date, time, sender_group, text = match.groups()

            # Determine the actual sender
            sender = sender_group.strip() if sender_group else "Sistema"

            current_message = {
                "date": date,
                "time": time,
                "sender": sender,
                "text": text.strip()
            }
            # Add sender to detected participants if it's not a system message
            if sender != "Sistema":
                detected_participants.add(sender)
        elif current_message:
            # If it's not a new message, it's a continuation of the previous message
            current_message["text"] += '\n' + line.strip()

    # Add the last message if it exists
    if current_message:
        messages.append(current_message)

    # Return messages and the list of detected participants
    return messages, list(detected_participants)

def display_message_bubble(sender_name, text, time, use_green_bubble_style):
    """
    Displays a single chat message bubble using Streamlit's markdown.
    sender_name: The name of the sender to display.
    text: The message content.
    time: The message timestamp.
    use_green_bubble_style: True if it should use the 'my-message' style (green), False for 'other-message' style (white).
    """
    # Determine CSS classes based on desired bubble style
    message_class = "my-message" if use_green_bubble_style else "other-message"
    sender_color_class = "my-sender-color" if use_green_bubble_style else "other-sender-color"

    # Handle multimedia and YouTube link placeholders
    message_text = text
    if "<Multimedia omitido>" in message_text:
        message_text = "[Multimedia Omitido]"
    elif "https://youtube.com/shorts/" in message_text:
        message_text = f"[Video de YouTube] {message_text}"

    # HTML structure for a single message bubble
    st.markdown(f"""
        <div class="message-bubble {message_class}">
            <div class="message-sender-name {sender_color_class}">
                {sender_name}
            </div>
            <div>{message_text}</div>
            <div class="message-time">
                {time}
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- Streamlit App Layout ---
st.set_page_config(page_title="Visualizador de Chat de WhatsApp", layout="centered")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
        /* Import Font Awesome for icons */
        @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css');

        html, body, [class*="st-"] {
            font-family: "Inter", sans-serif;
            color: #333;
        }
        /* El fondo de toda la aplicación (fuera del chat-container) */
        .stApp {
            background-color: #f0f2f5; /* Color de fondo general */
        }
        /* El contenedor principal del chat, ahora con la imagen de fondo */
        .chat-container {
            /*background-image: url('https://i.pinimg.com/736x/3a/2e/99/3a2e99d16f179dae33e2c394be2229fb.jpg'); */
            background-size: cover;
            background-position: center;
            background-attachment: local; /* Permite que el fondo se desplace con el contenido si el contenedor es scrollable */
            background-repeat: no-repeat;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            padding: 20px;
            margin-top: 20px;
            border: 1px solid rgba(0, 0, 0, 0.1); /* Borde fino al cuadro de conversación */
        }
        .chat-header {
            background-color: #075e54;
            color: white;
            padding: 16px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            font-weight: bold;
            text-align: center;
            margin: -20px -20px 20px -20px; /* Adjust to cover padding */
        }
        .chat-messages-area {
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            max-height: 70vh; /* Max height for the messages area */
            padding: 20px; /* Padding for the entire message area */
            background-color: transparent; /* Aseguramos que no tenga color de fondo propio */
        }
        .message-bubble {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 18px;
            margin-bottom: 8px;
            word-wrap: break-word;
            line-height: 1.4;
            position: relative;
            border: 1px solid rgba(0, 0, 0, 0.1); /* Borde fino para las burbujas de mensaje */
        }
        /* Styles for "my" messages (right-aligned) - ahora con transparencia */
        .message-bubble.my-message {
            background-color: rgba(220, 248, 198, 0.85); /* Light green con 85% de opacidad */
            border-bottom-right-radius: 4px;
        }
        /* Styles for "other" messages (left-aligned) - ahora con transparencia y tono beige claro */
        .message-bubble.other-message {
            background-color: rgba(245, 245, 220, 0.85); /* Beige claro con 85% de opacidad */
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 0.5px rgba(0, 0, 0, 0.13);
        }
        /* Sender name styling */
        .message-sender-name {
            font-weight: bold;
            font-size: 0.85rem;
            margin-bottom: 2px;
        }
        .my-sender-color {
            color: #075e54; /* Dark green for user's sender name */
        }
        .other-sender-color {
            color: #34b7f1; /* Blue for other sender names */
        }
        /* Message time styling */
        .message-time {
            font-size: 0.7rem;
            color: #888;
            text-align: right;
            margin-top: 4px;
        }
        /* Style for the button */
        .stButton>button {
            background-color: #25d366;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.3s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            border: none;
        }
        .stButton>button:hover {
            background-color: #1da851;
        }
        /* New style for hash info box */
        .hash-info-box {
            background-color: #e7f3ff; /* Light blue for information */
            border-left: 5px solid #2196F3; /* Blue border on the left */
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            font-size: 0.9em;
            color: #333;
            width: 100%; /* Asegura que ocupe todo el ancho disponible */
        }
        .hash-info-box strong {
            color: #0056b3;
        }
        .hash-info-box .hash-value {
            display: inline-block; /* Permite aplicar padding y background sin romper la línea */
            word-break: break-all; /* Permite que los hashes largos se rompan en cualquier punto */
            color: #495057; /* Color gris oscuro para los hashes */
            padding: 0px 0px; /* Espaciado interno para el hash */
            border-radius: 4px; /* Bordes ligeramente redondeados para el hash */
            font-size: 0.95em; /* Ligeramente más grande para el hash */
            margin-left: 5px; /* Pequeño margen para separar del label */
        }
        /* Estilo para la firma profesional */
        .professional-signature {
            text-align: center;
            margin-top: 30px;
            padding: 15px;
            background-color: #e9ecef; /* Un gris claro para el fondo */
            border-radius: 8px;
            border: 1px solid #ced4da;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        .professional-signature p {
            margin: 5px 0;
            font-size: 0.95em;
            color: #495057;
        }
        .professional-signature strong {
            color: #212529;
            font-size: 1.1em;
        }
        /* Estilo para la descripción de la herramienta */
        .tool-description {
            text-align: justify;
            margin-top: 10px;
            margin-bottom: 20px;
            padding: 10px 20px;
            background-color: #e6f7ff; /* Un azul muy claro */
            border-left: 5px solid #007bff; /* Borde azul para destacar */
            border-radius: 8px;
            font-size: 0.9em;  /* Puedes eliminar esta línea o ajustarla */
            color: #333;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        .tool-description p {
            font-size: 0.85em; /* Ajusta este valor para hacer la letra más pequeña */
            margin: 0; /* Elimina el margen por defecto de los párrafos si no lo necesitas */
        }
    </style>
""", unsafe_allow_html=True)

# Título de la aplicación con icono de WhatsApp
st.markdown("## <i class='fab fa-whatsapp'></i> Visualizador de Chat de WhatsApp", unsafe_allow_html=True)

# Descripción de la herramienta
st.markdown("""
    <div class="tool-description">
        <p> Esta aplicación ha sido diseñada por Marcelo G. Montiel, Analista Universitario de Sistemas - Universidad Tecnológica Nacional, con el propósito de optimizar la visualización de los chats exportados de WhatsApp. Ofreciendo una interfaz gráfica que emula la experiencia original de WhatsApp, esta herramienta facilita una lectura y análisis más eficientes de las conversaciones. Adicionalmente, incorpora funcionalidades técnicas, como el cálculo de hashes, lo cual es de particular relevancia en el ámbito de las Pericias Informáticas para la verificación de la integridad de los datos. El código fuente de esta herramienta se encuentra a disposición para aquellos interesados en su estudio y aplicación, bajo la premisa de:
        <strong> "Que la sabiduría no sea humillación para tú prójimo. Omar Khayyam".</strong></p> 
    </div>
""", unsafe_allow_html=True)

# Initialize session state for alignment if not already set
if 'invert_alignment' not in st.session_state:
    st.session_state.invert_alignment = False
if 'participant1' not in st.session_state:
    st.session_state.participant1 = None
if 'participant2' not in st.session_state:
    st.session_state.participant2 = None

# File uploader for WhatsApp chat .txt file
uploaded_file = st.file_uploader("Carga tu archivo de chat de WhatsApp (.txt)", type=["txt"])
st.info("¡Hola! Para empezar, por favor, selecciona un archivo de chat de WhatsApp (.txt).")
# Button to toggle message alignment
if st.button("Invertir Posición de Mensajes"):
    st.session_state.invert_alignment = not st.session_state.invert_alignment

if uploaded_file is not None:
    # Read the file content
    file_content_bytes = uploaded_file.read() # Read as bytes for hashing
    file_content = file_content_bytes.decode("utf-8")

    # Calculate SHA256 and MD5 hashes
    sha256_hash = hashlib.sha256(file_content_bytes).hexdigest()
    md5_hash = hashlib.md5(file_content_bytes).hexdigest()

    # Display file information and hashes in a highlighted box using st.expander
    with st.expander("📊 Información y Hashes del Archivo Cargado", expanded=True):
        # Utilizar divs para cada línea de información para un mejor control del layout
        # y asegurar que el label y el valor estén en la misma línea.
        st.markdown(f"""
            <div class="hash-info-box">
                <div><strong>Nombre del archivo:</strong> {uploaded_file.name}</div>
                <div><strong>Tamaño del archivo:</strong> {uploaded_file.size / 1024:.2f} KB</div>
                <div><strong>Hash SHA256:</strong> <span class="hash-value">{sha256_hash}</span></div>
                <div><strong>Hash MD5:</strong> <span class="hash-value">{md5_hash}</span></div>
            </div>
        """, unsafe_allow_html=True)

    # Parse the chat content and get detected participants
    messages, detected_participants = parse_chat_content(file_content)

    # Filter out "Sistema" from detected participants
    actual_participants = [p for p in detected_participants if p != "Sistema"]

    if not messages:
        st.error("No se encontraron mensajes en el formato esperado. Asegúrate de que el archivo sea un chat exportado de WhatsApp.")
    else:
        # Identify the two main participants for alignment
        if len(actual_participants) >= 2:
            # Always pick the first two detected participants for alignment
            st.session_state.participant1 = actual_participants[0]
            st.session_state.participant2 = actual_participants[1]
        elif len(actual_participants) == 1:
            st.session_state.participant1 = actual_participants[0]
            st.session_state.participant2 = None # Only one participant
            st.warning(f"Solo se detectó un participante principal: '{st.session_state.participant1}'. La inversión de posición no tendrá efecto.")
        else:
            st.session_state.participant1 = None
            st.session_state.participant2 = None
            st.warning("No se detectaron suficientes participantes para alinear el chat (se necesitan al menos dos).")
        
        # Display identified participants for user info
        st.info(f"Participantes identificados en el chat: **{', '.join(actual_participants) if actual_participants else 'Ninguno (solo mensajes del sistema)'}**")

        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        st.markdown("<div class='chat-header'>Conversación</div>", unsafe_allow_html=True) # Re-agregado el título "Conversación"

        # Use a container for the scrollable chat messages area
        with st.container():
            st.markdown("<div class='chat-messages-area'>", unsafe_allow_html=True)
            
            if st.session_state.participant1 and st.session_state.participant2:
                # Determine who is on the left and who is on the right based on inversion state
                if not st.session_state.invert_alignment:
                    left_aligned_participant = st.session_state.participant1
                    right_aligned_participant = st.session_state.participant2
                else:
                    left_aligned_participant = st.session_state.participant2
                    right_aligned_participant = st.session_state.participant1
             #   st.info(f"Mensajes de **{left_aligned_participant}** a la izquierda (burbuja blanca). Mensajes de **{right_aligned_participant}** a la derecha (burbuja verde).")
                for msg in messages:
                    # Handle system messages first
                    if msg["sender"] == "Sistema":
                        st.markdown(f"""
                            <div style="text-align: center; font-size: 0.8em; color: #666; margin: 5px 0;">
                                {msg["text"]}
                            </div>
                        """, unsafe_allow_html=True)
                        continue

                    sender_lower = msg["sender"].lower()

                    if sender_lower == right_aligned_participant.lower():
                        # Message goes to the right column, uses green bubble style
                        col1, col2 = st.columns([1, 4]) # Smaller left, larger right
                        with col2:
                            display_message_bubble(msg["sender"], msg["text"], f"{msg['date']} {msg['time']}", True) # True for green bubble
                    elif sender_lower == left_aligned_participant.lower():
                        # Message goes to the left column, uses white bubble style
                        col1, col2 = st.columns([4, 1]) # Larger left, smaller right
                        with col1:
                            display_message_bubble(msg["sender"], msg["text"], f"{msg['date']} {msg['time']}", False) # False for white bubble
                    else:
                        # Fallback for any other unexpected sender in a multi-person chat
                        st.markdown(f"""
                            <div style="text-align: center; font-size: 0.8em; color: #666; margin: 5px 0;">
                                {msg["text"]}
                            </div>
                        """, unsafe_allow_html=True)
            else:
                # If not enough participants for two-sided alignment, display all messages neutrally
                for msg in messages:
                    if msg["sender"] == "Sistema":
                        st.markdown(f"""
                            <div style="text-align: center; font-size: 0.8em; color: #666; margin: 5px 0;">
                                {msg["text"]}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div class="message-bubble other-message">
                                <div class="message-sender-name other-sender-color">
                                    {msg["sender"]}
                                </div>
                                <div>{msg["text"]}</div>
                                <div class="message-time">
                                    {msg['date']} {msg['time']}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True) # Close chat-messages-area
        
        st.markdown("</div>", unsafe_allow_html=True) # Close chat-container
#else:
 #   st.info("¡Hola! Para empezar, por favor, selecciona un archivo de chat de WhatsApp (.txt).")

# HTML/JS para el contador de visitas de Firebase
firebase_counter_html = """
<script src="https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js"></script>
<script src="https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js"></script>
<script src="https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js"></script>
<div id="visit_counter_display" style="font-size: 0.9em; color: #555; text-align: center; margin-top: 10px;">Cargando visitas...</div>
<script>
    // Asegurarse de que Streamlit esté listo antes de ejecutar el script
    window.addEventListener('load', function() {
        // Acceder a las variables globales proporcionadas por el entorno de Canvas
        // Usar un fallback seguro en caso de que las variables no estén definidas
        const firebaseConfig = JSON.parse(window.__firebase_config || '{}');
        const appId = window.__app_id || 'default-app-id';
        const initialAuthToken = window.__initial_auth_token;

        // Verificar si la configuración de Firebase es válida
        if (Object.keys(firebaseConfig).length === 0) {
            console.error("Configuración de Firebase no encontrada. No se puede inicializar Firebase.");
            document.getElementById('visit_counter_display').innerText = "Contador no disponible (configuración Firebase faltante).";
            return;
        }

        // Inicializar Firebase
        const app = firebase_app.initializeApp(firebaseConfig);
        const auth = firebase_auth.getAuth(app);
        const db = firebase_firestore.getFirestore(app);

        async function updateVisitCounter() {
            try {
                // Iniciar sesión anónimamente si no hay token personalizado
                if (initialAuthToken) {
                    await firebase_auth.signInWithCustomToken(auth, initialAuthToken);
                } else {
                    await firebase_auth.signInAnonymously(auth);
                }

                // Referencia al documento del contador en Firestore
                // La ruta sigue las reglas de seguridad: /artifacts/{appId}/public/data/app_visits/counter
                const counterDocRef = firebase_firestore.doc(db, `artifacts/${appId}/public/data/app_visits/counter`);

                // Usar una transacción para incrementar el contador de forma segura
                await firebase_firestore.runTransaction(db, async (transaction) => {
                    const sfDoc = await transaction.get(counterDocRef);
                    // Obtener el conteo actual o 0 si no existe
                    const newCount = (sfDoc.exists ? sfDoc.data().count : 0) + 1;
                    // Actualizar el documento con el nuevo conteo
                    transaction.set(counterDocRef, { count: newCount }, { merge: true });
                });

                // Configurar un listener en tiempo real para el contador
                // Esto asegura que el contador se actualice si otros usuarios lo incrementan
                firebase_firestore.onSnapshot(counterDocRef, (docSnapshot) => {
                    if (docSnapshot.exists()) {
                        const currentCount = docSnapshot.data().count;
                        document.getElementById('visit_counter_display').innerText = `Visitas totales: ${currentCount}`;
                    } else {
                        document.getElementById('visit_counter_display').innerText = `Visitas totales: 0`;
                    }
                }, (error) => {
                    console.error("Error al escuchar el contador de visitas:", error);
                    document.getElementById('visit_counter_display').innerText = "Error al cargar el contador de visitas.";
                });

            } catch (error) {
                console.error("Error al inicializar o incrementar el contador:", error);
                document.getElementById('visit_counter_display').innerText = "Error al cargar el contador.";
            }
        }

        updateVisitCounter(); // Llamar a la función para iniciar el contador
    });
</script>
"""
# Información profesional al final de la aplicación
st.markdown("""
    <div class="professional-signature">
        <p>Diseñado por <strong>Marcelo G. Montiel</strong></p>
        <p>Analista Universitario de Sistemas - Universidad Tecnológica Nacional</p>
        <p>San Miguel de Tucumán, Tucumán, Argentina</p>
    </div>
""", unsafe_allow_html=True)
