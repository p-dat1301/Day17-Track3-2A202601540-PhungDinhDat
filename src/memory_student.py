from __future__ import annotations

from typing import Any

from .config import settings
from .context_budget import ContextBudgetManager
from .utils import cap_query, join_nonempty
from .zep_common import prime_eval_thread, render_graph_search


class StudentMemory:
    """Only this file needs to be edited by students."""

    def __init__(self, client: Any):
        self.client = client
        self.budget = ContextBudgetManager(settings.context_tokens)

    # NOTE: Zep rejects graph.search queries longer than 400 characters. Some
    # eval queries are longer than that, so wrap every query with
    # `cap_query(query)` (see src/utils.py) before passing it to graph.search.

    def retrieve_long_term(self, user_id: str, thread_id: str, query: str) -> str:
        # LAB TODO 1/4
        # 1) prime_eval_thread(...) rebuilds a fresh thread holding just the
        #    current query, so Zep can assemble a relevance-ranked Context Block
        #    from the user graph instead of dumping the whole transcript.
        prime_eval_thread(self.client, user_id, thread_id, query)

        # 2) Pull the assembled Context Block and return its `.context` string.
        user_context = self.client.thread.get_user_context(thread_id=thread_id)
        context_block = getattr(user_context, "context", "") or ""

        # 3) Bonus: surface raw facts/edges with their validity ranges. The
        #    Context Block alone can miss low-relevance open-loop deadlines or a
        #    superseded preference; the edge facts expose exactly that history.
        try:
            facts = self.client.graph.search(
                user_id=user_id,
                query=cap_query(query),
                scope="edges",
                limit=20,
            )
            fact_text = render_graph_search(facts)
        except Exception:
            fact_text = ""

        return join_nonempty([context_block, fact_text], sep="\n\n")

    def retrieve_episodic(self, user_id: str, query: str) -> str:
        # LAB TODO 2/4
        # Search only this user's episodes (user_id, NOT the shared graph_id)
        # so past trajectories stay user-scoped. scope="episodes" returns raw
        # source text that keeps literal markers (e.g. ASYNC-FIX-20).
        results = self.client.graph.search(
            user_id=user_id,
            query=cap_query(query),
            scope="episodes",
            limit=15,
        )
        # Verbose session messages can crowd out concise marker-bearing
        # reflections under the tight episodic budget, so cap each episode to
        # keep more distinct episodes within the budget.
        return render_graph_search(results, episode_char_cap=180)

    def retrieve_semantic(self, graph_id: str, query: str) -> str:
        # LAB TODO 3/4
        # Search the standalone domain graph (graph_id, NOT user_id). Shared
        # knowledge must not leak one user's personal facts into another query.
        q = cap_query(query)
        # scope="episodes" returns raw document text that keeps literal markers
        # (e.g. PAYMENT-RULE-3). The "auto" scope returns extracted facts that
        # DROP those literal codes, so avoid it here.
        try:
            results = self.client.graph.search(
                graph_id=graph_id,
                query=q,
                scope="episodes",
                limit=8,
            )
        except Exception:
            # Compatibility fallback for accounts/SDKs where episodes scope
            # differs; nodes still expose entity summaries.
            results = self.client.graph.search(
                graph_id=graph_id,
                query=q,
                scope="nodes",
                limit=8,
            )
        return render_graph_search(results)

    def assemble_context(self, layers: dict[str, str]) -> tuple[str, dict[str, dict[str, int]]]:
        # LAB TODO 4/4
        # ContextBudgetManager already enforces the 10/4/3/3 teaching budget and
        # the priority order short_term -> long_term -> episodic -> semantic.
        return self.budget.assemble(layers)
