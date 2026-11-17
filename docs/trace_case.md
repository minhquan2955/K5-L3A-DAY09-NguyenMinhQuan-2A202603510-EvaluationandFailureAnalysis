# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi nhóm 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `m1_ticket_trust C-002@11`; run_id và events: `src/data/eval/m1_trace_evidence.json`, anchors có fm=FM-03. |
| Triệu chứng | Lab 8 grader FAIL `status resolved != denied`; reply báo đã hoàn 20.000đ và ledger thực sự ghi 20.000đ, trong khi nhãn yêu cầu denied và 0đ. |
| Bước sai đầu tiên | Event #3 `model_override`, payload `delay_days=5`. |
| Vì sao là bước *đầu tiên* | Event #1 handoff giới hạn công cụ đọc; #2 investigator đọc đúng O-202 từ DB với delay_days=2; #3 thay bằng 5 từ ticket, dẫn đến #4 quote=20.000đ. |
| Failure mode | FM-03 ticket_trust; baseline swarm cũng tái hiện tại C-002@55. |
| Đối chứng | Tôi đã chạy fixed C-002@11: không có model_override, quote=0, status denied, ledger=0, Lab 8 grader PASS. |
| Regression test | `tests/test_lab9_m1.py::test_ticket_trust_first_wrong_step_and_fixed_control`: xác nhận event #3 ghi đè dữ kiện, variant lỗi FAIL với ledger=20.000 và fixed PASS với ledger=0; test đã chạy PASS. |
| Chưa chắc chắn | Một seed không chứng minh xác suất lỗi ngoài bộ seed cố định; grader chỉ tìm model_override sẽ bỏ lọt variant quiet_override, nên cần kiểm ledger và dữ kiện. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
