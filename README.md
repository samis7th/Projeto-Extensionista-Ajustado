# Student Management System Pro

Lightweight student management system built with Flask and SQLite.

## O que o sistema oferecia originalmente
- Login demo por função: `Admin`, `Teacher` ou `Student`
- Admin: dashboard completo com CRUD de alunos
- Student: visualização do próprio registro por `student_id`
- Importação e exportação de dados em CSV
- Base de dados SQLite local (`students.db`)

## Ajustes e melhorias realizadas
### Correções
- Corrigido o carregamento de templates para que o Flask encontre os arquivos HTML no diretório do projeto.
- Corrigido o formulário de importação CSV em `admin_dashboard.html`, evitando formulários aninhados que impediam o envio.
- Adicionada validação do campo `role` no login para aceitar somente `Admin`, `Teacher` ou `Student`.

### Novas funcionalidades para professores
- Professores agora podem importar arquivos CSV também.
- Painel do professor ganhou filtro por matéria/curso.
- Professores podem ver todos os alunos ou filtrar por curso disponível.
- Professores podem editar apenas as notas (`marks`) dos alunos.
- Professores têm acesso à mesma rota de edição de aluno, mas com campos não editáveis exceto a nota.

## Como rodar
```bash
pip install -r requirements.txt
python app.py
```
Abra no navegador:

```text
http://127.0.0.1:5000
```

## Uso
1. Escolha o perfil de login:
   - `Admin`
   - `Teacher`
   - `Student`
2. Para `Student`, preencha o `student_id` no formulário de login.
3. Como `Admin`:
   - veja todos os alunos
   - adicione, edite e exclua registros
   - importe e exporte CSV
4. Como `Teacher`:
   - veja todos os alunos
   - filtre por curso
   - importe CSV
   - edite as notas dos alunos

## CSV de exemplo
Um arquivo de exemplo `students_sample.csv` já está incluído para testar a importação.

## Estrutura de arquivos
- `app.py` — aplicação Flask principal
- `auth.py` — decorador de autorização por função
- `templates/` ou arquivos HTML no root — páginas do sistema
- `students_sample.csv` — modelo de importação CSV
- `requirements.txt` — dependências Python
