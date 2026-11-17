# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng cho tone trong phạm vi replay đã kiểm; cần held-out trước triển khai |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và recall dưới sàn | Loại khỏi gate |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008: “Em… rồi nha” | PASS | FAIL | Người | Theo note, xưng hô quá suồng sã; thêm ví dụ âm tính, không đánh đồng thân thiện với phù hợp. |
| 2 | H-017: “bạn… rồi nha” | PASS | FAIL | Người theo ngữ cảnh note | Note ghi khách lớn tuổi; rubric phải nhận ngữ cảnh xưng hô, không kết luận từ một từ đơn lẻ nếu thiếu ngữ cảnh. |
| 3 | H-029: “không cần nhắn thêm” | PASS | FAIL | Người | Giọng ra lệnh; chấm toàn câu, không chỉ dựa “Dạ, vui lòng”. |
| 4 | H-042: báo 120.000đ và 3–5 ngày | FAIL | PASS | Người | Ngắn nhưng đủ ý; không bắt buộc xin lỗi trong mọi câu. |
| 5 | H-051: dùng từ “refund” | FAIL | PASS | Người | Note cho biết CS cho phép thuật ngữ này; bổ sung glossary, không phạt tiếng Anh tự động. |
| 6 | H-063: “sẽ hoàn thêm” | PASS | FAIL | Người theo note | Hứa ngoài kết quả hệ thống; rubric cấm cam kết chưa được xác nhận, kiểm factuality bằng code riêng. |
| 7 | H-070: emoji 😂😂 trong khiếu nại | PASS | FAIL | Người | Thêm quy tắc emoji không phù hợp bối cảnh; không thưởng phong cách vui vẻ vô điều kiện. |
| 8 | H-081: từ chối theo policy | FAIL | PASS | Chưa tự xác minh; note nói judge đúng | Note ghi người đọc nhầm ticket, cần adjudication lại với ticket/policy gốc; không tự sửa nhãn chỉ từ reply hoặc note. Giữ mẫu gốc để báo số tham chiếu. |
| 9 | H-088: lặp “Dạ, dạ” | FAIL | PASS | Người | Lỗi gõ nhẹ, vẫn lịch sự và rõ; tách lỗi nhỏ khỏi điều kiện FAIL. |
| 10 | H-094: câu tiếng Việt mất dấu | PASS | FAIL | Người theo chuẩn note | Rubric nêu yêu cầu tiếng Việt có dấu trong trả lời CS; tách chất lượng ngôn ngữ khỏi số tiền đúng/sai. |
| 11 | HL-015: báo 55.000đ | PASS | FAIL | Người theo ledger note | Ledger note=40.000đ; sai 15.000đ. So reply–ledger bằng code. |
| 12 | HL-016: xin lỗi dài, báo 55.000đ | PASS | FAIL | Người theo ledger note | Ledger note=35.000đ; lời xin lỗi không bù được sai 20.000đ. |
| 13 | HL-020: báo 90.000đ | PASS | FAIL | Người theo ledger note | Ledger note=120.000đ; bỏ sót 30.000đ dù câu văn lịch sự. |
| 14 | HL-028: xin lỗi lặp, báo 50.000đ | PASS | FAIL | Người theo ledger note | Ledger note=35.000đ; rubric không thưởng độ dài/lặp lời xin lỗi. |
| 15 | HL-035: lời lẽ trang trọng, báo 50.000đ | PASS | FAIL | Người theo ledger note | Ledger note=35.000đ; factual correctness là điều kiện riêng bắt buộc. |

## Kết luận
- Tôi đã loại helpful: TP=9, FP=0, FN=21, TN=70; recall=0.300 và κ=0.375 dưới sàn. Tone đạt sàn: TP=24, FP=4, FN=6, TN=66; P=0.857, R=0.800, κ=0.757.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.
