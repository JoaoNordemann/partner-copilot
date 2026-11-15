# Auditoria de segredos e privacidade

Padrões usados, sem imprimir os valores encontrados:

| Alvo | Expressão |
| --- | --- |
| Hugging Face | `hf_[A-Za-z0-9]{20,}` |
| GitHub | `gh[pousr]_[A-Za-z0-9]{20,}` e `github_pat_[A-Za-z0-9_]{25,}` |
| Variável Hugging Face | `HF_TOKEN[ \t]*=[ \t]*[^\s#]+`; revisar atribuições vazias separadamente |
| Windows e diretórios pessoais | `C:[/\\]+Users[/\\]+` e busca literal pelos nomes de pastas pessoais conhecidos |
| E-mails | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` |

Use `git log --all -G '<expressão>' --format=%h --name-only -- .`
para localizar alterações históricas e `git grep -Il -E '<expressão>'`
para listar arquivos versionados com correspondências. Abra cada ZIP
localmente e aplique os mesmos padrões ao conteúdo descompactado, incluindo
subarquivos. Confira também as células de saída e a aba Logs da versão salva
do Kaggle. Registre nomes de arquivos e contagens sem copiar credenciais.

A busca histórica encontrou apenas a atribuição vazia de HF_TOKEN.
A inspeção complementar cobriu a aba Logs do benchmark T4, o ZIP do
benchmark, os três membros textuais do ZIP B2W recebido e os logs locais
da API, do treino e do smoke. Os padrões verificados ficaram sem
correspondências nesses artefatos. O histórico de versões do editor da
avaliação ABSA não apresentou uma execução salva com aba Logs própria.
A inspeção dessa avaliação cobre as saídas visíveis no editor e o ZIP
B2W disponível localmente. Antes de publicar uma execução privada,
repita a conferência da versão escolhida, incluindo logs e arquivos de saída.

A revogação das credenciais compartilhadas fora do repositório segue
sem confirmação.
