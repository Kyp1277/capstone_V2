# JobFit Evaluation Dataset

Dataset ini berisi CV synthetic/anonymized untuk smoke test akurasi rekomendasi. Tujuannya bukan menggantikan validasi manusia, tetapi memberi bukti bahwa sistem tidak selalu mendorong semua CV ke role IT.

Setiap case memuat:

- `cvText`: ringkasan CV teks yang aman untuk test.
- `expectedSkills`: skill yang seharusnya terbaca.
- `expectedTopRoleKeywords`: kata kunci yang diharapkan muncul pada rekomendasi teratas.
- `forbiddenTopRoleKeywords`: kata kunci yang tidak boleh mendominasi rekomendasi teratas.

Jalankan dari root project:

```powershell
python backend\modules\test_recommendation_evaluation.py
```
