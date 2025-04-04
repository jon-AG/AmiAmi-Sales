async def main():
    results = await scrape()
    print(f"\n📦 Finished scraping. Total products found: {len(results)}")

    final_results = []
    for condition, title, link, discounted_str, original_str, img_url in results:
        try:
            discounted = int(discounted_str.replace(" JPY", "").replace(",", ""))
            original = int(original_str.replace(" JPY", "").replace(",", ""))
            discount_percent = round((original - discounted) / original * 100, 2)
            final_results.append({
                "Condition": condition,
                "Title": title,
                "Link": link,
                "Image": img_url,
                "Discounted Price": f"{discounted:,} JPY",
                "Original Price": f"{original:,} JPY",
                "Discount %": f"{discount_percent}%"
            })
        except Exception as e:
            print(f"⚠️ Error processing item '{title}': {e}")
            continue

    # ✅ Sort by Discount %, descending
    final_results.sort(
        key=lambda x: float(x["Discount %"].replace("%", "")),
        reverse=True
    )

    # Save to CSV
    with open("AmiAmi_sales.csv", "w", encoding="utf-8") as f:
        f.write("Condition|Title|Link|Discounted Price|Original Price|Discount|Image\n")
        for item in final_results:
            f.write(f"{item['Condition']}|{item['Title']}|{item['Link']}|{item['Discounted Price']}|{item['Original Price']}|{item['Discount %']}|{item['Image']}\n")
    print("✅ Saved to AmiAmi_sales.csv")

    # Save to Markdown
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("### 📦 AmiAmi Discounted Figures\n\n")
        f.write("| Condition | Pic | Title | Discounted Price | Original Price | Discount | Link |\n")
        f.write("|-----------|-----|-------|------------------|----------------|----------|------|\n")
        for item in final_results:
            f.write(f"| {item['Condition']} | ![]({item['Image']}) | {item['Title']} | {item['Discounted Price']} | {item['Original Price']} | {item['Discount %']} | [Link]({item['Link']}) |\n")
    print("✅ Saved to README.md")

    # Save to Excel with filters, auto width and custom formatting for the Title column
    df = pd.DataFrame(final_results)
    excel_filename = "AmiAmi_sales.xlsx"
    with pd.ExcelWriter(excel_filename, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        # Add an autofilter to the header row.
        worksheet.autofilter(0, 0, len(df.index), len(df.columns) - 1)

        # Create a format for the Title column with text wrap.
        title_format = workbook.add_format({"text_wrap": True})

        # Set column widths. For Title, use fixed width and wrap text.
        for i, col in enumerate(df.columns):
            if col == "Title":
                worksheet.set_column(i, i, 50, title_format)
            else:
                column_data = df[col].astype(str)
                max_len = max(column_data.map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
    print(f"✅ Saved to {excel_filename}")

    # Optional print preview
    for item in final_results:
        print(f"Condition:       {item['Condition']}")
        print(f"Title:           {item['Title']}")
        print(f"Link:            {item['Link']}")
        print(f"Image:           {item['Image']}")
        print(f"Discounted Price:{item['Discounted Price']}")
        print(f"Original Price:  {item['Original Price']}")
        print(f"Discount:        {item['Discount %']}\n")
