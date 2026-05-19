$ErrorActionPreference = "Stop"

Write-Host "Instalando dependências do Electron..."
npm install

Write-Host "Gerando instalador Windows..."
npm run dist

Write-Host ""
Write-Host "Instalador gerado em: desktop\etisul-admin\dist"
Write-Host "Execute o instalador para criar o atalho 'Etisul Admin' na área de trabalho."
