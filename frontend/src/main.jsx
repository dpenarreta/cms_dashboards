import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
// Tipografía de la identidad base (Sora, IBM Plex Sans/Mono), empaquetada en vez de pedirla a
// Google Fonts: el servidor está en la intranet y no se puede contar con salida a internet.
import '@fontsource/sora/500.css'
import '@fontsource/sora/600.css'
import '@fontsource/sora/700.css'
import '@fontsource/sora/800.css'
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/500.css'
import '@fontsource/ibm-plex-sans/600.css'
import '@fontsource/ibm-plex-sans/700.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import '@fontsource/ibm-plex-mono/600.css'
import './styles/dashboard.css'
import './styles/directorio.css'
// Identidad base de la Matriz (copia literal) y, después, su puente con las clases de este
// proyecto: el orden importa, cada hoja pisa a la anterior.
import './styles/matriz.css'
import './styles/identidad-cms.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
