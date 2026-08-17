# Lab 17 — Submission

## 1. Layer quan trọng nhất trong bộ test này

Long-term (Context Block) — quyết định 4 case E02, E03, E08, E09 (20đ) và là nền cho E07 mixed. Nó tái hiện cross-session preference (E02), open-loop deadline (E03), recency/conflict (E08) và user isolation (E09).

## 2. Trade-off: Zep Context Block vs Redis + Qdrant

Zep `thread.get_user_context` tự assemble context theo relevance từ user graph (facts + episodes + validity), kèm provenance và recency sẵn có. Redis/Qdrant tự build phải tự viết KV có TTL, vector hoá, xếp hạng và gộp lại — kiểm soát hoàn toàn nhưng tốn công, dễ sót scope và conflict. Lab dùng Redis/Qdrant làm baseline để thấy managed vs tự build.

## 3. Guardrail chống memory poisoning

Chỉ ingest khi có consent opt-in (`require_memory_consent`); minimize PII (redact email/phone) trước khi ghi; durable write phải có source/timestamp/scope (MEMORY_SCHEMA.md); conflict dùng recency + scope, giữ fact cũ cho provenance; heartbeat không tự cấp quyền mới.

## Phân tích benchmark (11/11 = 100% vs no-memory 2/11 = 18.2%)

1. **Layer hit rate thấp nhất:** memory-enabled mọi layer đều 100%. Trong baseline no-memory, long_term/episodic/semantic đều 0% — ba layer durable phụ thuộc hoàn toàn vào Zep retrieval.
2. **Query nhiều token nhất:** E03 (open-loop deadline, 1368 token) vì Context Block kéo toàn bộ user summary; kế là E02 (1356), E08 (1349).
3. **E07 mixed:** cần long_term (preference `Python`) + semantic (`Idempotency-Key`). Evidence bắt buộc: cả hai marker cùng xuất hiện trong merged context.
4. **Token reduction:** memory 14.2% vs no-memory 81.8%. No-memory reduction cao vì retrieve 0 token (trả rỗng) → rẻ nhưng hit rate 18.2%. Reduction chỉ có nghĩa khi đi kèm hit rate.

## E08 recency

Sau stage 3, `BLUEBIRD-42` yêu cầu `TypeScript`/`NestJS` cho project công ty, còn `ORCHID-27` vẫn giữ `Python`. Context Block ưu tiên fact mới theo recency + scope mà không xoá preference cũ — đúng rule conflict của MEMORY.md.

## E10 compaction

Sliding window giữ `REVIEW-DEADLINE-1600`, `Friday`, `16:00` trong DURABLE_NOTES dù raw turn đã bị evict. Compaction ưu tiên constraint/deadline/state (không tóm tắt văn hoa); buffer không nén nên token tăng tuyến tính và mất constraint khi tràn.
