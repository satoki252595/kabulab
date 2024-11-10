import getStockFinancialInfo as gsfi
import screening as s
import createNotionDataFrame as cndf
import notionUp

codeList = [code + '.T' for code in gsfi.getStockCodeDataFrame()['code'].tolist()]
screened_stocks = s.screen_stocks(codeList)
notionUpDataFrame = cndf.createNotionUpDataFrame(screened_stocks)
notionUp.uploadToNotion(notionUpDataFrame)
