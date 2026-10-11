# Excel hücre ve formül denetimi

Kaynak SHA-256: `097593e3ed599f1bcd9507ec42b28166c7d8080e5af5a8b4ab678a4280ad9430`

Tek sayfa: Sayfa1. Dolu içerik 1–97. satırlar arasındadır; kullanılan alan biçimlendirme nedeniyle 110. satıra uzanır. Boş satırlar da tarandı. Kaynak dosya değiştirilmedi.

175 formül bağımsız yeniden hesaplandı ve kayıtlı değerleriyle 1e-12 toleransta eşleşti. Bu işlem Excel uygulamasında yeniden hesaplama değildir. Matematiksel hata içeren formül de kendi kayıtlı sonucuyla eşleşebilir.

## Satır bazında bütün dolu hücreler

### Satır 1

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A1 | `Matris 1(A,B ve C arası)` | — | Etiket veya sabit girdi. |
| G1 | `Normalize Edilmiş Matris ve Ağırlıkları` | — | Etiket veya sabit girdi. |

### Satır 2

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| B2 | `A` | — | Etiket veya sabit girdi. |
| C2 | `B` | — | Etiket veya sabit girdi. |
| D2 | `C` | — | Etiket veya sabit girdi. |
| H2 | `A` | — | Etiket veya sabit girdi. |
| I2 | `B` | — | Etiket veya sabit girdi. |
| J2 | `C` | — | Etiket veya sabit girdi. |
| K2 | `Ağırlık(%)` | — | Etiket veya sabit girdi. |

### Satır 3

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A3 | `A` | — | Etiket veya sabit girdi. |
| B3 | `1` | — | Etiket veya sabit girdi. |
| C3 | `5` | — | Etiket veya sabit girdi. |
| D3 | `9` | — | Etiket veya sabit girdi. |
| G3 | `A` | — | Etiket veya sabit girdi. |
| H3 | `=B3/(B4+B5+B3)` | 0.7627118644067796 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I3 | `=C3/(C4+C5+C3)` | 0.7894736842105263 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J3 | `=D3/(D4+D5+D3)` | 0.6923076923076923 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K3 | `=SUM(H3:J3)/3` | 0.7481644136416662 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 4

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A4 | `B` | — | Etiket veya sabit girdi. |
| B4 | `0.2` | — | Etiket veya sabit girdi. |
| C4 | `1` | — | Etiket veya sabit girdi. |
| D4 | `3` | — | Etiket veya sabit girdi. |
| G4 | `B` | — | Etiket veya sabit girdi. |
| H4 | `=B4/(B3+B4+B5)` | 0.15254237288135594 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I4 | `=C4/(C3+C4+C5)` | 0.15789473684210528 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J4 | `=D4/(D3+D4+D5)` | 0.23076923076923078 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K4 | `=SUM(H4:J4)/3` | 0.180402113497564 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 5

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A5 | `C` | — | Etiket veya sabit girdi. |
| B5 | `0.1111111111111111` | — | Etiket veya sabit girdi. |
| C5 | `0.3333333333333333` | — | Etiket veya sabit girdi. |
| D5 | `1` | — | Etiket veya sabit girdi. |
| G5 | `C` | — | Etiket veya sabit girdi. |
| H5 | `=B5/(B3+B4+B5)` | 0.0847457627118644 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I5 | `=C5/(C3+C4+C5)` | 0.05263157894736842 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J5 | `=D5/(D3+D4+D5)` | 0.07692307692307693 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K5 | `=SUM(H5:J5)/3` | 0.07143347286076991 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 6

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A6 | `Sütun Toplamı` | — | Etiket veya sabit girdi. |
| B6 | `=SUM(B3:B5)` | 1.3111111111111111 | Sütun/ağırlık toplamını kontrol eder. |
| C6 | `=SUM(C3:C5)` | 6.333333333333333 | Sütun/ağırlık toplamını kontrol eder. |
| D6 | `=SUM(D3:D5)` | 13 | Sütun/ağırlık toplamını kontrol eder. |
| G6 | `Sütun Toplamı` | — | Etiket veya sabit girdi. |
| H6 | `=SUM(H3:H5)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| I6 | `=SUM(I3:I5)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| J6 | `=SUM(J3:J5)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| K6 | `=SUM(K3:K5)` | 1 | Sütun/ağırlık toplamını kontrol eder. |

### Satır 9

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A9 | `Tutarlılık Analizi` | — | Etiket veya sabit girdi. |

### Satır 10

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| B10 | `Matris 1*Ağırlık Vektörü` | — | Etiket veya sabit girdi. |
| C10 | `Matris 1/Ağırlık` | — | Etiket veya sabit girdi. |
| D10 | `Ortalama` | — | Etiket veya sabit girdi. |

### Satır 11

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A11 | `A` | — | Etiket veya sabit girdi. |
| B11 | `=(B3*K3+C3*K4+D3*K5)` | 2.2930762368764155 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C11 | `=B11/K3` | 3.064936256076309 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D11 | `=C11/3` | 1.021645418692103 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 12

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A12 | `B` | — | Etiket veya sabit girdi. |
| B12 | `=(B4*K3+C4*K4+D4*K5)` | 0.544335414808207 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C12 | `=B12/K4` | 3.0173449980981366 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D12 | `=C12/3` | 1.0057816660327121 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 13

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A13 | `C` | — | Etiket veya sabit girdi. |
| B13 | `=(B5*K3+C5*K4+D5*K5)` | 0.2146968899868097 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C13 | `=B13/K5` | 3.005550218806703 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D13 | `=C13/3` | 1.0018500729355677 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 14

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A14 | `λmax` | — | Etiket veya sabit girdi. |
| B14 | `=SUM(D11:D13)` | 3.029277157660383 | Bileşenlerin ortalaması → yaklaşık λmax; kesin özdeğer değildir. |
| E14 | ` ` | — | Etiket veya sabit girdi. |

### Satır 15

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A15 | `CI` | — | Etiket veya sabit girdi. |
| B15 | `=(B14-3)/(3-1)` | 0.014638578830191484 | (λ−n)/(n−1) → CI. |

### Satır 16

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A16 | `CR` | — | Etiket veya sabit girdi. |
| B16 | `=B15/0.58` | 0.025238929017571528 | CI / boyuta uygun RI → yaklaşık CR. |

### Satır 17

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A17 | `CR^<=0,10` | — | Etiket veya sabit girdi. |
| B17 | `Tutarlı` | — | Sabit durum metni; CR değişince güncellenmez. |

### Satır 20

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A20 | `Matris 2 (Grup A İçi(K1,K2,K9))` | — | Etiket veya sabit girdi. |
| G20 | `Normalize Edilmiş Matris ve Ağırlıkları` | — | Etiket veya sabit girdi. |

### Satır 21

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| B21 | `K1` | — | Etiket veya sabit girdi. |
| C21 | `K2` | — | Etiket veya sabit girdi. |
| D21 | `K9` | — | Etiket veya sabit girdi. |
| H21 | `K1` | — | Etiket veya sabit girdi. |
| I21 | `K2` | — | Etiket veya sabit girdi. |
| J21 | `K9` | — | Etiket veya sabit girdi. |
| K21 | `Ağırlık(%)` | — | Etiket veya sabit girdi. |

### Satır 22

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A22 | `K1` | — | Etiket veya sabit girdi. |
| B22 | `1` | — | Etiket veya sabit girdi. |
| C22 | `1` | — | Etiket veya sabit girdi. |
| D22 | `2` | — | Etiket veya sabit girdi. |
| G22 | `K1` | — | Etiket veya sabit girdi. |
| H22 | `=B22/(B23+B24+B22)` | 0.4 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I22 | `=C22/(C23+C24+C22)` | 0.4 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J22 | `=D22/(D23+D24+D22)` | 0.4 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K22 | `=SUM(H22:J22)/3` | 0.4000000000000001 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 23

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A23 | `K2` | — | Etiket veya sabit girdi. |
| B23 | `1` | — | Etiket veya sabit girdi. |
| C23 | `1` | — | Etiket veya sabit girdi. |
| D23 | `2` | — | Etiket veya sabit girdi. |
| G23 | `K2` | — | Etiket veya sabit girdi. |
| H23 | `=B23/(B22+B23+B24)` | 0.4 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I23 | `=C23/(C22+C23+C24)` | 0.4 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J23 | `=D23/(D22+D23+D24)` | 0.4 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K23 | `=SUM(H23:J23)/3` | 0.4000000000000001 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 24

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A24 | `K9` | — | Etiket veya sabit girdi. |
| B24 | `0.5` | — | Etiket veya sabit girdi. |
| C24 | `0.5` | — | Etiket veya sabit girdi. |
| D24 | `1` | — | Etiket veya sabit girdi. |
| G24 | `K9` | — | Etiket veya sabit girdi. |
| H24 | `=B24/(B22+B23+B24)` | 0.2 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I24 | `=C24/(C22+C23+C24)` | 0.2 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J24 | `=D24/(D22+D23+D24)` | 0.2 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K24 | `=SUM(H24:J24)/3` | 0.20000000000000004 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 25

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A25 | `Sütun Toplamı` | — | Etiket veya sabit girdi. |
| B25 | `=SUM(B22:B24)` | 2.5 | Sütun/ağırlık toplamını kontrol eder. |
| C25 | `=SUM(C22:C24)` | 2.5 | Sütun/ağırlık toplamını kontrol eder. |
| D25 | `=SUM(D22:D24)` | 5 | Sütun/ağırlık toplamını kontrol eder. |
| G25 | `Sütun Toplamı` | — | Etiket veya sabit girdi. |
| H25 | `=SUM(H22:H24)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| I25 | `=SUM(I22:I24)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| J25 | `=SUM(J22:J24)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| K25 | `=SUM(K22:K24)` | 1.0000000000000002 | Sütun/ağırlık toplamını kontrol eder. |

### Satır 28

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A28 | `Tutarlılık Analizi` | — | Etiket veya sabit girdi. |

### Satır 29

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| B29 | `Matris 1*Ağırlık Vektörü` | — | Etiket veya sabit girdi. |
| C29 | `Matris 1/Ağırlık` | — | Etiket veya sabit girdi. |
| D29 | `Ortalama` | — | Etiket veya sabit girdi. |

### Satır 30

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A30 | `K1` | — | Etiket veya sabit girdi. |
| B30 | `=(B22*K22+C22*K23+D22*K24)` | 1.2000000000000002 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C30 | `=B30/K22` | 3 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D30 | `=C30/3` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 31

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A31 | `K2` | — | Etiket veya sabit girdi. |
| B31 | `=(B23*K22+C23*K23+D23*K24)` | 1.2000000000000002 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C31 | `=B31/K23` | 3 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D31 | `=C31/3` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 32

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A32 | `K9` | — | Etiket veya sabit girdi. |
| B32 | `=(B24*K22+C24*K23+D24*K24)` | 0.6000000000000001 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C32 | `=B32/K24` | 3 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D32 | `=C32/3` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 33

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A33 | `λmax` | — | Etiket veya sabit girdi. |
| B33 | `=SUM(D30:D32)` | 3 | Bileşenlerin ortalaması → yaklaşık λmax; kesin özdeğer değildir. |

### Satır 34

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A34 | `CI` | — | Etiket veya sabit girdi. |
| B34 | `=(B33-3)/(3-1)` | 0 | (λ−n)/(n−1) → CI. |

### Satır 35

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A35 | `CR` | — | Etiket veya sabit girdi. |
| B35 | `=B34/0.58` | 0 | CI / boyuta uygun RI → yaklaşık CR. |

### Satır 36

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A36 | `CR^<=0,10` | — | Etiket veya sabit girdi. |
| B36 | `Tutarlı` | — | Sabit durum metni; CR değişince güncellenmez. |

### Satır 39

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A39 | `Matris 3 (Grup B İçi(K6, K7, K8, K10))` | — | Etiket veya sabit girdi. |
| G39 | `Normalize Edilmiş Matris ve Ağırlıkları` | — | Etiket veya sabit girdi. |

### Satır 40

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| B40 | `K6` | — | Etiket veya sabit girdi. |
| C40 | `K7` | — | Etiket veya sabit girdi. |
| D40 | `K8` | — | Etiket veya sabit girdi. |
| E40 | `K10` | — | Etiket veya sabit girdi. |
| H40 | `K6` | — | Etiket veya sabit girdi. |
| I40 | `K7` | — | Etiket veya sabit girdi. |
| J40 | `K8` | — | Etiket veya sabit girdi. |
| K40 | `K10` | — | Etiket veya sabit girdi. |
| L40 | `Ağırlık(%)` | — | Etiket veya sabit girdi. |

### Satır 41

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A41 | `K6` | — | Etiket veya sabit girdi. |
| B41 | `1` | — | Etiket veya sabit girdi. |
| C41 | `1` | — | Etiket veya sabit girdi. |
| D41 | `1` | — | Etiket veya sabit girdi. |
| E41 | `1` | — | Etiket veya sabit girdi. |
| G41 | `K6` | — | Etiket veya sabit girdi. |
| H41 | `=B41/(B42+B43+B41+B44)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I41 | `=C41/(C42+C43+C41+C44)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J41 | `=D41/(D42+D43+D41+D44)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K41 | `=E41/(E42+E43+E41+E44)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| L41 | `=SUM(H41:J41)/3` | 0.25 | HATA: Dört yerine üç normalize sütunun ortalaması → yerel ağırlık; K sütunu dışlanmış. |

### Satır 42

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A42 | `K7` | — | Etiket veya sabit girdi. |
| B42 | `1` | — | Etiket veya sabit girdi. |
| C42 | `1` | — | Etiket veya sabit girdi. |
| D42 | `1` | — | Etiket veya sabit girdi. |
| E42 | `1` | — | Etiket veya sabit girdi. |
| G42 | `K7` | — | Etiket veya sabit girdi. |
| H42 | `=B42/(B43+B44+B42+B41)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I42 | `=C42/(C43+C44+C42+C41)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J42 | `=D42/(D43+D44+D42+D41)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K42 | `=E42/(E43+E44+E42+E41)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| L42 | `=SUM(H42:J42)/3` | 0.25 | HATA: Dört yerine üç normalize sütunun ortalaması → yerel ağırlık; K sütunu dışlanmış. |

### Satır 43

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A43 | `K8` | — | Etiket veya sabit girdi. |
| B43 | `1` | — | Etiket veya sabit girdi. |
| C43 | `1` | — | Etiket veya sabit girdi. |
| D43 | `1` | — | Etiket veya sabit girdi. |
| E43 | `1` | — | Etiket veya sabit girdi. |
| G43 | `K8` | — | Etiket veya sabit girdi. |
| H43 | `=B43/(B44+B41+B42+B43)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I43 | `=C43/(C44+C41+C42+C43)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J43 | `=D43/(D44+D41+D42+D43)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K43 | `=E43/(E44+E41+E42+E43)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| L43 | `=SUM(H43:J43)/3` | 0.25 | HATA: Dört yerine üç normalize sütunun ortalaması → yerel ağırlık; K sütunu dışlanmış. |

### Satır 44

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A44 | `K10` | — | Etiket veya sabit girdi. |
| B44 | `1` | — | Etiket veya sabit girdi. |
| C44 | `1` | — | Etiket veya sabit girdi. |
| D44 | `1` | — | Etiket veya sabit girdi. |
| E44 | `1` | — | Etiket veya sabit girdi. |
| G44 | `K10` | — | Etiket veya sabit girdi. |
| H44 | `=B44/(B41+B42+B44+B43)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I44 | `=C44/(C41+C42+C44+C43)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J44 | `=D44/(D41+D42+D44+D43)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K44 | `=E44/(E41+E42+E44+E43)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| L44 | `=SUM(H44:J44)/3` | 0.25 | HATA: Dört yerine üç normalize sütunun ortalaması → yerel ağırlık; K sütunu dışlanmış. |

### Satır 45

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A45 | `Sütun Toplamı` | — | Etiket veya sabit girdi. |
| B45 | `=SUM(B41:B44)` | 4 | Sütun/ağırlık toplamını kontrol eder. |
| C45 | `=SUM(C41:C44)` | 4 | Sütun/ağırlık toplamını kontrol eder. |
| D45 | `=SUM(D41:D44)` | 4 | Sütun/ağırlık toplamını kontrol eder. |
| E45 | `=SUM(E41:E44)` | 4 | Sütun/ağırlık toplamını kontrol eder. |
| G45 | `Sütun Toplamı` | — | Etiket veya sabit girdi. |
| H45 | `=SUM(H41:H44)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| I45 | `=SUM(I41:I44)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| J45 | `=SUM(J41:J44)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| K45 | `=SUM(K41:K44)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| L45 | `=SUM(L41:L44)` | 1 | Sütun/ağırlık toplamını kontrol eder. |

### Satır 48

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A48 | `Tutarlılık Analizi` | — | Etiket veya sabit girdi. |

### Satır 49

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| B49 | `Matris 1*Ağırlık Vektörü` | — | Etiket veya sabit girdi. |
| C49 | `Matris 1/Ağırlık` | — | Etiket veya sabit girdi. |
| D49 | `Ortalama` | — | Etiket veya sabit girdi. |

### Satır 50

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A50 | `K6` | — | Etiket veya sabit girdi. |
| B50 | `=(B41*L41+C41*L42+D41*L43+E41*L44)` | 1 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C50 | `=B50/L41` | 4 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D50 | `=C50/4` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 51

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A51 | `K7` | — | Etiket veya sabit girdi. |
| B51 | `=(B42*L41+C42*L42+D42*L43+E42*L44)` | 1 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C51 | `=B51/L42` | 4 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D51 | `=C51/4` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 52

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A52 | `K8` | — | Etiket veya sabit girdi. |
| B52 | `=(B43*L41+C43*L42+D43*L43+E43*L44)` | 1 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C52 | `=B52/L43` | 4 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D52 | `=C52/4` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 53

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A53 | `K10` | — | Etiket veya sabit girdi. |
| B53 | `=(B44*L41+C44*L42+D44*L43+E44*L44)` | 1 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C53 | `=B53/L44` | 4 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D53 | `=C53/4` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 54

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A54 | `λmax` | — | Etiket veya sabit girdi. |
| B54 | `=SUM(D50:D53)` | 4 | Bileşenlerin ortalaması → yaklaşık λmax; kesin özdeğer değildir. |

### Satır 55

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A55 | `CI` | — | Etiket veya sabit girdi. |
| B55 | `=(B54-4)/(4-1)` | 0 | (λ−n)/(n−1) → CI. |

### Satır 56

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A56 | `CR` | — | Etiket veya sabit girdi. |
| B56 | `=B55/0.9` | 0 | CI / boyuta uygun RI → yaklaşık CR. |

### Satır 57

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A57 | `CR^<=0,10` | — | Etiket veya sabit girdi. |
| B57 | `Tutarlı` | — | Sabit durum metni; CR değişince güncellenmez. |

### Satır 60

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A60 | `Matris 4 (Grup C İçi(K3,K4,K5))` | — | Etiket veya sabit girdi. |
| G60 | `Normalize Edilmiş Matris ve Ağırlıkları` | — | Etiket veya sabit girdi. |

### Satır 61

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| B61 | `K3` | — | Etiket veya sabit girdi. |
| C61 | `K4` | — | Etiket veya sabit girdi. |
| D61 | `K5` | — | Etiket veya sabit girdi. |
| H61 | `K3` | — | Etiket veya sabit girdi. |
| I61 | `K4` | — | Etiket veya sabit girdi. |
| J61 | `K5` | — | Etiket veya sabit girdi. |
| K61 | `Ağırlık(%)` | — | Etiket veya sabit girdi. |

### Satır 62

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A62 | `K3` | — | Etiket veya sabit girdi. |
| B62 | `1` | — | Etiket veya sabit girdi. |
| C62 | `2` | — | Etiket veya sabit girdi. |
| D62 | `2` | — | Etiket veya sabit girdi. |
| G62 | `K3` | — | Etiket veya sabit girdi. |
| H62 | `=B62/(B63+B64+B62)` | 0.5 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I62 | `=C62/(C63+C64+C62)` | 0.5 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J62 | `=D62/(D63+D64+D62)` | 0.5 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K62 | `=SUM(H62:J62)/3` | 0.5 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 63

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A63 | `K4` | — | Etiket veya sabit girdi. |
| B63 | `0.5` | — | Etiket veya sabit girdi. |
| C63 | `1` | — | Etiket veya sabit girdi. |
| D63 | `1` | — | Etiket veya sabit girdi. |
| G63 | `K4` | — | Etiket veya sabit girdi. |
| H63 | `=B63/(B62+B63+B64)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I63 | `=C63/(C62+C63+C64)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J63 | `=D63/(D62+D63+D64)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K63 | `=SUM(H63:J63)/3` | 0.25 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 64

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A64 | `K5` | — | Etiket veya sabit girdi. |
| B64 | `0.5` | — | Etiket veya sabit girdi. |
| C64 | `1` | — | Etiket veya sabit girdi. |
| D64 | `1` | — | Etiket veya sabit girdi. |
| G64 | `K5` | — | Etiket veya sabit girdi. |
| H64 | `=B64/(B62+B63+B64)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| I64 | `=C64/(C62+C63+C64)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| J64 | `=D64/(D62+D63+D64)` | 0.25 | Ham karşılaştırmayı kendi sütun toplamına böler → normalize matris. |
| K64 | `=SUM(H64:J64)/3` | 0.25 | Normalize satır ortalaması → yerel ağırlık. |

### Satır 65

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A65 | `Sütun Toplamı` | — | Etiket veya sabit girdi. |
| B65 | `=SUM(B62:B64)` | 2 | Sütun/ağırlık toplamını kontrol eder. |
| C65 | `=SUM(C62:C64)` | 4 | Sütun/ağırlık toplamını kontrol eder. |
| D65 | `=SUM(D62:D64)` | 4 | Sütun/ağırlık toplamını kontrol eder. |
| G65 | `Sütun Toplamı` | — | Etiket veya sabit girdi. |
| H65 | `=SUM(H62:H64)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| I65 | `=SUM(I62:I64)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| J65 | `=SUM(J62:J64)` | 1 | Sütun/ağırlık toplamını kontrol eder. |
| K65 | `=SUM(K62:K64)` | 1 | Sütun/ağırlık toplamını kontrol eder. |

### Satır 68

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A68 | `Tutarlılık Analizi` | — | Etiket veya sabit girdi. |

### Satır 69

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| B69 | `Matris 1*Ağırlık Vektörü` | — | Etiket veya sabit girdi. |
| C69 | `Matris 1/Ağırlık` | — | Etiket veya sabit girdi. |
| D69 | `Ortalama` | — | Etiket veya sabit girdi. |

### Satır 70

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A70 | `K1` | — | Etiket veya sabit girdi. |
| B70 | `=(B62*K62+C62*K63+D62*K64)` | 1.5 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C70 | `=B70/K62` | 3 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D70 | `=C70/3` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 71

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A71 | `K2` | — | Etiket veya sabit girdi. |
| B71 | `=(B63*K62+C63*K63+D63*K64)` | 0.75 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C71 | `=B71/K63` | 3 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D71 | `=C71/3` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 72

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A72 | `K9` | — | Etiket veya sabit girdi. |
| B72 | `=(B64*K62+C64*K63+D64*K64)` | 0.75 | Ham matris satırı × ağırlık vektörü → (Aw)i. |
| C72 | `=B72/K64` | 3 | (Aw)i / wi → özdeğer yaklaşım bileşeni. |
| D72 | `=C72/3` | 1 | Özdeğer yaklaşım bileşeni / n → ortalamaya katkı. |

### Satır 73

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A73 | `λmax` | — | Etiket veya sabit girdi. |
| B73 | `=SUM(D70:D72)` | 3 | Bileşenlerin ortalaması → yaklaşık λmax; kesin özdeğer değildir. |

### Satır 74

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A74 | `CI` | — | Etiket veya sabit girdi. |
| B74 | `=(B73-3)/(3-1)` | 0 | (λ−n)/(n−1) → CI. |

### Satır 75

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A75 | `CR` | — | Etiket veya sabit girdi. |
| B75 | `=B74/0.58` | 0 | CI / boyuta uygun RI → yaklaşık CR. |

### Satır 76

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A76 | `CR^<=0,10` | — | Etiket veya sabit girdi. |
| B76 | `Tutarlı` | — | Sabit durum metni; CR değişince güncellenmez. |

### Satır 79

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A79 | `Global Ağırlıklar` | — | Etiket veya sabit girdi. |
| G79 | `Genel Tutarlılık Değerlendirmesi` | — | Etiket veya sabit girdi. |

### Satır 80

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A80 | `Kod ` | — | Etiket veya sabit girdi. |
| B80 | `Kriter` | — | Etiket veya sabit girdi. |
| C80 | `Ana Kriter` | — | Etiket veya sabit girdi. |
| D80 | `Yerel Ağırlık` | — | Etiket veya sabit girdi. |
| E80 | `Global Ağırlık` | — | Etiket veya sabit girdi. |
| G80 | `Matris` | — | Etiket veya sabit girdi. |
| H80 | `CR` | — | Etiket veya sabit girdi. |
| I80 | `Durum` | — | Etiket veya sabit girdi. |

### Satır 81

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A81 | `K1` | — | Etiket veya sabit girdi. |
| B81 | `CPCI İndeksleme` | — | Etiket veya sabit girdi. |
| C81 | `=K3` | 0.7481644136416662 | Üst grubun yerel ağırlığını getirir. |
| D81 | `=K22` | 0.4000000000000001 | Kriterin grup içi yerel ağırlığını getirir. |
| E81 | `=C81*D81` | 0.29926576545666655 | Üst grup × yerel ağırlık → global ağırlık. |
| G81 | `Ana Kriterler (A-B-C)` | — | Etiket veya sabit girdi. |
| H81 | `0.0251` | — | Elle girilmiş CR özeti; hesaplanan CR hücresine bağlı değil. |
| I81 | `Tutarlı` | — | Sabit durum metni; CR değişince güncellenmez. |

### Satır 82

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A82 | `K2` | — | Etiket veya sabit girdi. |
| B82 | `Akademik Temsiliyet` | — | Etiket veya sabit girdi. |
| C82 | `=K3` | 0.7481644136416662 | Üst grubun yerel ağırlığını getirir. |
| D82 | `=K23` | 0.4000000000000001 | Kriterin grup içi yerel ağırlığını getirir. |
| E82 | `=C82*D82` | 0.29926576545666655 | Üst grup × yerel ağırlık → global ağırlık. |
| G82 | `Grup A (K1-K2-K9)` | — | Etiket veya sabit girdi. |
| H82 | `0` | — | Elle girilmiş CR özeti; hesaplanan CR hücresine bağlı değil. |
| I82 | `Tutarlı` | — | Sabit durum metni; CR değişince güncellenmez. |

### Satır 83

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A83 | `K3` | — | Etiket veya sabit girdi. |
| B83 | `Maliyet` | — | Etiket veya sabit girdi. |
| C83 | `=K5` | 0.07143347286076991 | Üst grubun yerel ağırlığını getirir. |
| D83 | `=K62` | 0.5 | Kriterin grup içi yerel ağırlığını getirir. |
| E83 | `=C83*D83` | 0.035716736430384956 | Üst grup × yerel ağırlık → global ağırlık. |
| G83 | `Grup B (K10-K8-K6-K7)` | — | Etiket veya sabit girdi. |
| H83 | `0` | — | Elle girilmiş CR özeti; hesaplanan CR hücresine bağlı değil. |
| I83 | `Tutarlı` | — | Sabit durum metni; CR değişince güncellenmez. |

### Satır 84

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A84 | `K4` | — | Etiket veya sabit girdi. |
| B84 | `Katılım Formatı` | — | Etiket veya sabit girdi. |
| C84 | `=K5` | 0.07143347286076991 | Üst grubun yerel ağırlığını getirir. |
| D84 | `=K63` | 0.25 | Kriterin grup içi yerel ağırlığını getirir. |
| E84 | `=C84*D84` | 0.017858368215192478 | Üst grup × yerel ağırlık → global ağırlık. |
| G84 | `Grup C (K3-K4-K5)` | — | Etiket veya sabit girdi. |
| H84 | `0` | — | Elle girilmiş CR özeti; hesaplanan CR hücresine bağlı değil. |
| I84 | `Tutarlı` | — | Sabit durum metni; CR değişince güncellenmez. |

### Satır 85

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A85 | `K5` | — | Etiket veya sabit girdi. |
| B85 | `Konum` | — | Etiket veya sabit girdi. |
| C85 | `=K5` | 0.07143347286076991 | Üst grubun yerel ağırlığını getirir. |
| D85 | `=K64` | 0.25 | Kriterin grup içi yerel ağırlığını getirir. |
| E85 | `=C85*D85` | 0.017858368215192478 | Üst grup × yerel ağırlık → global ağırlık. |

### Satır 86

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A86 | `K6` | — | Etiket veya sabit girdi. |
| B86 | `Süreklilik Statüsü` | — | Etiket veya sabit girdi. |
| C86 | `=K4` | 0.180402113497564 | Üst grubun yerel ağırlığını getirir. |
| D86 | `=L41` | 0.25 | Kriterin grup içi yerel ağırlığını getirir. |
| E86 | `=C86*D86` | 0.045100528374391 | Üst grup × yerel ağırlık → global ağırlık. |

### Satır 87

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A87 | `K7` | — | Etiket veya sabit girdi. |
| B87 | `Konu Özgünlüğü` | — | Etiket veya sabit girdi. |
| C87 | `=K4` | 0.180402113497564 | Üst grubun yerel ağırlığını getirir. |
| D87 | `=L42` | 0.25 | Kriterin grup içi yerel ağırlığını getirir. |
| E87 | `=C87*D87` | 0.045100528374391 | Üst grup × yerel ağırlık → global ağırlık. |

### Satır 88

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A88 | `K8` | — | Etiket veya sabit girdi. |
| B88 | `Geçmiş Veri Şeffaflığı` | — | Etiket veya sabit girdi. |
| C88 | `=K4` | 0.180402113497564 | Üst grubun yerel ağırlığını getirir. |
| D88 | `=L43` | 0.25 | Kriterin grup içi yerel ağırlığını getirir. |
| E88 | `=C88*D88` | 0.045100528374391 | Üst grup × yerel ağırlık → global ağırlık. |

### Satır 89

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A89 | `K9` | — | Etiket veya sabit girdi. |
| B89 | `Uluslararası Kapsam` | — | Etiket veya sabit girdi. |
| C89 | `=K3` | 0.7481644136416662 | Üst grubun yerel ağırlığını getirir. |
| D89 | `=K24` | 0.20000000000000004 | Kriterin grup içi yerel ağırlığını getirir. |
| E89 | `=C89*D89` | 0.14963288272833328 | Üst grup × yerel ağırlık → global ağırlık. |

### Satır 90

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A90 | `K10` | — | Etiket veya sabit girdi. |
| B90 | `Katılımcı Memnuniyeti` | — | Etiket veya sabit girdi. |
| C90 | `=K4` | 0.180402113497564 | Üst grubun yerel ağırlığını getirir. |
| D90 | `=L44` | 0.25 | Kriterin grup içi yerel ağırlığını getirir. |
| E90 | `=C90*D90` | 0.045100528374391 | Üst grup × yerel ağırlık → global ağırlık. |

### Satır 93

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A93 | `Kongre Adı` | — | Etiket veya sabit girdi. |
| B93 | `K1` | — | Etiket veya sabit girdi. |
| C93 | `K2` | — | Etiket veya sabit girdi. |
| D93 | `K3` | — | Etiket veya sabit girdi. |
| E93 | `K4` | — | Etiket veya sabit girdi. |
| F93 | `K5` | — | Etiket veya sabit girdi. |
| G93 | `K6` | — | Etiket veya sabit girdi. |
| H93 | `K7` | — | Etiket veya sabit girdi. |
| I93 | `K8` | — | Etiket veya sabit girdi. |
| J93 | `K9` | — | Etiket veya sabit girdi. |
| K93 | `K10` | — | Etiket veya sabit girdi. |
| L93 | `Puan(0-100)` | — | Etiket veya sabit girdi. |
| M93 | `Durum` | — | Etiket veya sabit girdi. |

### Satır 94

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A94 | `A Kongresi` | — | Etiket veya sabit girdi. |
| B94 | `1` | — | Etiket veya sabit girdi. |
| C94 | `1` | — | Etiket veya sabit girdi. |
| D94 | `0` | — | Etiket veya sabit girdi. |
| E94 | `0` | — | Etiket veya sabit girdi. |
| F94 | `0` | — | Etiket veya sabit girdi. |
| G94 | `1` | — | Etiket veya sabit girdi. |
| H94 | `1` | — | Etiket veya sabit girdi. |
| I94 | `1` | — | Etiket veya sabit girdi. |
| J94 | `0` | — | Etiket veya sabit girdi. |
| K94 | `0` | — | Etiket veya sabit girdi. |
| L94 | `=(B94*$E$81+C94*$E$82+D94*$E$83+E94*$E$84+F94*$E$85+G94*$E$86+H94*$E$87+I94*$E$88+J94*$E$89+K94*$E$90)*100` | 73.38331160365063 | Kriter skoru × global ağırlık toplamı ×100 → kongre puanı. |
| M94 | `=IF(L94="","",IF(L94>=90,"Geçerli",IF(L94>=70,"Ortalama","Geçersiz")))` | Ortalama | 90 ve 70 eşikleriyle durum; puanın boş olup olmadığını kontrol eder, kriter eksiklerini kontrol etmez. |

### Satır 95

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A95 | `B kongresi` | — | Etiket veya sabit girdi. |
| B95 | `1` | — | Etiket veya sabit girdi. |
| C95 | `1` | — | Etiket veya sabit girdi. |
| D95 | `0` | — | Etiket veya sabit girdi. |
| E95 | `0` | — | Etiket veya sabit girdi. |
| F95 | `0` | — | Etiket veya sabit girdi. |
| G95 | `0` | — | Etiket veya sabit girdi. |
| H95 | `0` | — | Etiket veya sabit girdi. |
| I95 | `0` | — | Etiket veya sabit girdi. |
| J95 | `1` | — | Etiket veya sabit girdi. |
| K95 | `0` | — | Etiket veya sabit girdi. |
| L95 | `=(B95*$E$81+C95*$E$82+D95*$E$83+E95*$E$84+F95*$E$85+G95*$E$86+H95*$E$87+I95*$E$88+J95*$E$89+K95*$E$90)*100` | 74.81644136416664 | Kriter skoru × global ağırlık toplamı ×100 → kongre puanı. |
| M95 | `=IF(L95="","",IF(L95>=90,"Geçerli",IF(L95>=70,"Ortalama","Geçersiz")))` | Ortalama | 90 ve 70 eşikleriyle durum; puanın boş olup olmadığını kontrol eder, kriter eksiklerini kontrol etmez. |

### Satır 96

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A96 | `C Kongresi` | — | Etiket veya sabit girdi. |
| B96 | `1` | — | Etiket veya sabit girdi. |
| C96 | `1` | — | Etiket veya sabit girdi. |
| D96 | `0` | — | Etiket veya sabit girdi. |
| E96 | `0` | — | Etiket veya sabit girdi. |
| F96 | `1` | — | Etiket veya sabit girdi. |
| G96 | `1` | — | Etiket veya sabit girdi. |
| H96 | `1` | — | Etiket veya sabit girdi. |
| I96 | `1` | — | Etiket veya sabit girdi. |
| J96 | `1` | — | Etiket veya sabit girdi. |
| K96 | `1` | — | Etiket veya sabit girdi. |
| L96 | `=(B96*$E$81+C96*$E$82+D96*$E$83+E96*$E$84+F96*$E$85+G96*$E$86+H96*$E$87+I96*$E$88+J96*$E$89+K96*$E$90)*100` | 94.64248953544231 | Kriter skoru × global ağırlık toplamı ×100 → kongre puanı. |
| M96 | `=IF(L96="","",IF(L96>=90,"Geçerli",IF(L96>=70,"Ortalama","Geçersiz")))` | Geçerli | 90 ve 70 eşikleriyle durum; puanın boş olup olmadığını kontrol eder, kriter eksiklerini kontrol etmez. |

### Satır 97

| Hücre | İçerik / formül | Kayıtlı sonuç | Matematiksel / yapısal anlam |
|---|---|---|---|
| A97 | `D kongresi` | — | Etiket veya sabit girdi. |
| B97 | `0` | — | Etiket veya sabit girdi. |
| C97 | `0` | — | Etiket veya sabit girdi. |
| D97 | `1` | — | Etiket veya sabit girdi. |
| E97 | `1` | — | Etiket veya sabit girdi. |
| F97 | `1` | — | Etiket veya sabit girdi. |
| G97 | `1` | — | Etiket veya sabit girdi. |
| H97 | `1` | — | Etiket veya sabit girdi. |
| I97 | `1` | — | Etiket veya sabit girdi. |
| J97 | `1` | — | Etiket veya sabit girdi. |
| K97 | `1` | — | Etiket veya sabit girdi. |
| L97 | `=(B97*$E$81+C97*$E$82+D97*$E$83+E97*$E$84+F97*$E$85+G97*$E$86+H97*$E$87+I97*$E$88+J97*$E$89+K97*$E$90)*100` | 40.14684690866672 | Kriter skoru × global ağırlık toplamı ×100 → kongre puanı. |
| M97 | `=IF(L97="","",IF(L97>=90,"Geçerli",IF(L97>=70,"Ortalama","Geçersiz")))` | Geçersiz | 90 ve 70 eşikleriyle durum; puanın boş olup olmadığını kontrol eder, kriter eksiklerini kontrol etmez. |
