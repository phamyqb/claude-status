# Claude Code status line for Warp

Status line nằm trong giao diện `claude` chạy trong Warp, không phải thanh toàn cục của Warp.
Cần Python 3.8+; không cần dependency hoặc Nerd Font.

## Cài đặt / cập nhật

Giải nén vào Downloads, rồi chạy trong Warp:

```sh
cd ~/Downloads/claude-statusline-warp
python3 install.py
```

Khi chạy trong terminal, bộ cài mở menu checkbox; mặc định tick tất cả.

- ↑ / ↓: di chuyển giữa các mục.
- Space: tick / bỏ tick mục hiện tại.
- Enter: xác nhận lựa chọn.
- A: chọn tất cả; N: bỏ chọn tất cả.
- Q / Esc / Ctrl+C: hủy, không sửa file.

Phải chọn ít nhất một mục. Enter xác nhận rồi cài ngay, không có bước chọn khoảng cách.
Menu dùng curses có sẵn trong Python trên macOS/Linux, không cần pip.
Nếu môi trường không hỗ trợ menu, dùng --show hoặc --yes.
Terminal được khôi phục khi xác nhận hoặc hủy menu.

Cài nhanh, không hỏi:

```sh
python3 install.py --yes
```

Chỉ hiện thông tin model / Git / app / effort:

```sh
python3 install.py --show model,git,app,effort
```

Hiện tất cả:

```sh
python3 install.py --show all
```

Bật tất cả nghĩa là bật mọi mục có dữ liệu; trường thiếu vẫn được ẩn.
Chạy lại bộ cài để thay lựa chọn. Không cần sudo hoặc sửa .zshrc.

## Các mục

| Option | Nội dung |
| --- | --- |
| model | Tên model |
| git | Git branch; ẩn khi không có branch |
| app | Tên thư mục project hiện tại, không phải tên ứng dụng macOS |
| effort | Reasoning effort nếu có |
| context | Phần trăm context window còn lại |
| current | Quota 5 giờ còn lại và thời gian reset |
| week | Quota 7 ngày còn lại và thời gian reset |
| cost | Ước tính chi phí API của phiên; không phải khoản thu thêm của gói thuê bao |
| duration | Thời lượng phiên do Claude Code báo |
| spend | Quota spend limit của gateway nếu có |

## Giao diện

Khung bo góc màu tím. Context / Current / Week thẳng cột, thanh mỏng dài 10 ô,
phần trăm rộng 3 cột. Current và Week luôn ở các hàng riêng.
Mỗi thanh đổi màu theo remaining: xanh >=50%, vàng >=20%, cam >=10%, đỏ <10%.
Ô vuông nhỏ ▪ thể hiện phần còn lại; ▫ thể hiện phần đã dùng.
Hai ký tự nằm giữa dòng thay vì sát đáy như các ký tự block thấp, giúp thanh
và nhãn Context / Current / Week cân đối hơn. Vị trí chính xác vẫn tùy font Warp.
Thanh giữ chiều rộng 10 ô. Các hàng sát nhau, không dòng trống hay đường phân cách;
chỉ giữ khung viền ngoài.
Ngày giờ reset theo múi giờ hệ điều hành, dạng DD-MMM-YYYY HH:mm, tên tháng tiếng Anh.
Đặt NO_COLOR=1 để tắt màu. Terminal hẹp thì dòng quota được xuống dòng.

## Cấu hình

Bộ cài lưu script và `statusline-config.json` trong `~/.claude`, đồng thời sửa duy nhất
trường `statusLine` trong `settings.json`, giữ các trường khác.
Nếu có `CLAUDE_CONFIG_DIR`, bộ cài dùng thư mục đó. Mọi file hiện có sắp sửa
được ghi đều được backup bằng đuôi `.backup-<thời gian>`.
Lựa chọn mặc định mỗi lần cài là show all.
Bộ cài dừng nếu settings JSON lỗi hoặc file đích là symlink.

Có thể sửa trực tiếp `statusline-config.json` sau khi cài:

```json
{
  "show": ["model", "app", "git", "effort", "context", "current", "week", "cost", "duration", "spend"]
}
```

Thay đổi xuất hiện lần render kế tiếp. File options lỗi thì script dùng mặc định.

## Dữ liệu và refresh

Context là không gian ngữ cảnh của model cho cuộc hội thoại, gồm lịch sử chat,
chỉ dẫn, nội dung file và kết quả tool; không phải RAM hoặc quota tài khoản.
Sau compact, context còn lại có thể tăng. Current là cửa sổ 5 giờ, Week là 7 ngày.
Theo tài liệu, quota thuê bao được mô tả cho Pro/Max; Team có thể thiếu các trường này.

Mặc định render theo sự kiện Claude Code. Có thể thêm `"refreshInterval": 5`
bên trong `statusLine` trên phiên bản hỗ trợ để chạy lại mỗi 5 giây.
Timer chỉ render JSON có sẵn, không tự fetch quota mới. Đồng hồ reset được tính lại.
Bản này không tự thêm refreshInterval khi cài.

## Bảo mật và gỡ cài đặt

Không đọc Keychain/token, gọi API hoặc lưu transcript/stdin. JSON được parse
bằng json.loads, không ghép vào mã. Dữ liệu hiển thị được lọc ký tự điều khiển.
Git chỉ đọc branch bằng mảng đối số, không shell, timeout 0.4 giây; khi ẩn Git
thì không chạy lệnh Git. Không vòng lặp nền, tput hay thay vị trí con trỏ.

Trong Claude Code chạy `/statusline remove` hoặc xóa trường `statusLine`.
Sau đó có thể xóa `statusline.py` và `statusline-config.json` trong thư mục cấu hình.
Khôi phục backup settings có thể ghi đè các thay đổi thực hiện sau thời điểm backup.

Tài liệu: https://code.claude.com/docs/en/statusline
Đã kiểm thử bằng dữ liệu giả/thư mục tạm, chưa chạy trực tiếp trên máy Mac của bạn.
